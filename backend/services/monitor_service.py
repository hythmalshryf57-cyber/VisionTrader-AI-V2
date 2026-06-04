import requests
import datetime
from fastapi import Request
from database import SessionLocal
import models
from services.telegram_bot import TelegramBot
from config import settings


class MonitorService:
    """Anti-VPN & Monitoring service: inspects requests, logs activity, detects VPN/proxy, alerts admins."""

    def __init__(self):
        self.telegram = TelegramBot(token=getattr(settings, 'TELEGRAM_BOT_TOKEN', None))

    def _get_client_ip(self, request: Request) -> str:
        xff = request.headers.get('x-forwarded-for') or request.headers.get('X-Forwarded-For')
        if xff:
            return xff.split(',')[0].strip()
        if getattr(request, 'client', None):
            return request.client.host
        return '0.0.0.0'

    def inspect_request(self, request: Request, action: str = None, current_user: models.User = None) -> dict:
        """Inspect an incoming request and log activity.

        Returns a dict with keys: `block` (bool), `reason` (str optional), `is_vpn` (bool)
        """
        ip = self._get_client_ip(request)
        user_agent = request.headers.get('user-agent', '')
        device_id = request.headers.get('x-device-id') or request.cookies.get('device_id') or request.headers.get('device-id')
        device_name = request.headers.get('x-device-name') or (user_agent[:250] if user_agent else None)
        action = action or str(request.url.path)

        # Query ip-api to detect proxy/hosting
        is_vpn = False
        location = None
        isp = None
        org = None
        try:
            resp = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,isp,org,query,proxy,hosting", timeout=3)
            j = resp.json() if resp.status_code == 200 else {}
            isp = j.get('isp')
            org = j.get('org')
            if j.get('status') == 'success':
                location = ", ".join(filter(None, [j.get('city'), j.get('regionName'), j.get('country')]))
                is_vpn = bool(j.get('proxy') or j.get('hosting') or ('VPN' in (isp or '').upper()) or ('VPN' in (org or '').upper()))
        except Exception:
            j = {}

        db = SessionLocal()
        try:
            activity = models.UserActivityMaster(
                user_id=current_user.id if current_user else None,
                action=action,
                ip=ip,
                device=device_id or device_name,
                location=location,
                is_vpn=is_vpn
            )
            db.add(activity)
            db.commit()

            # Device tracking
            if current_user and device_id:
                existing = db.query(models.UserDevice).filter(models.UserDevice.user_id == current_user.id, models.UserDevice.device_id == device_id).first()
                if not existing:
                    newdev = models.UserDevice(user_id=current_user.id, device_id=device_id, device_name=device_name, is_trusted=False)
                    db.add(newdev)
                    db.commit()
                    try:
                        self.telegram.alert_unknown_device(current_user.id, device_id, ip)
                    except Exception:
                        pass

            # Rapid location change detection
            if current_user:
                last = db.query(models.UserActivityMaster).filter(models.UserActivityMaster.user_id == current_user.id).order_by(models.UserActivityMaster.timestamp.desc()).offset(1).first()
                if last:
                    try:
                        diff = (activity.timestamp - last.timestamp).total_seconds()
                        if last.ip != ip and diff < 300:
                            try:
                                self.telegram.alert_multiple_locations(current_user.id, last.ip, ip)
                            except Exception:
                                pass
                    except Exception:
                        pass

            # If VPN detected -> block session and alert
            if is_vpn:
                if current_user:
                    u = db.query(models.User).filter(models.User.id == current_user.id).first()
                    if u:
                        u.force_logout_at = datetime.datetime.now(datetime.timezone.utc)
                        db.add(models.SecurityLog(user_id=current_user.id, event_type='vpn_block', ip_address=ip, description='VPN/Proxy detected - session blocked'))
                        db.commit()
                try:
                    self.telegram.alert_vpn_attempt(current_user.id if current_user else 'anonymous', ip, isp, org, action=action)
                except Exception:
                    pass
                return {"block": True, "reason": "VPN/Proxy detected"}

            return {"block": False, "is_vpn": is_vpn, "location": location}
        finally:
            db.close()

    def log_action(self, user_id: int, action: str, ip: str = None, device: str = None, location: str = None, is_vpn: bool = False):
        db = SessionLocal()
        try:
            act = models.UserActivityMaster(user_id=user_id, action=action, ip=ip, device=device, location=location, is_vpn=is_vpn)
            db.add(act)
            db.commit()
        finally:
            db.close()

    def block_user(self, user_id: int, reason: str = None):
        db = SessionLocal()
        try:
            u = db.query(models.User).filter(models.User.id == user_id).first()
            if u:
                u.force_logout_at = datetime.datetime.now(datetime.timezone.utc)
                u.is_active = False
                db.add(models.SecurityLog(user_id=user_id, event_type='blocked', ip_address=None, description=reason))
                db.commit()
        finally:
            db.close()


monitor_service = MonitorService()
import requests
from datetime import datetime, timezone
from database import SessionLocal
import models
from config import settings
from services.telegram_bot import TelegramBot


class MonitorService:
    def __init__(self):
        self.telegram = TelegramBot(token=getattr(settings, 'TELEGRAM_BOT_TOKEN', None))

    def _query_ip_api(self, ip: str) -> dict:
        try:
            resp = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,isp,org,as,query,proxy,hosting", timeout=3)
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}

    def inspect_request(self, request, action: str = None, current_user=None) -> dict:
        """
        Inspect incoming request: IP, UA, Device ID. Record activity and detect VPN/proxy.
        Returns a dict containing keys: block (bool), reason (str)
        """
        ip = None
        try:
            ip = request.client.host
        except Exception:
            ip = request.headers.get('x-forwarded-for', '').split(',')[0].strip() if request.headers.get('x-forwarded-for') else request.client.host if hasattr(request, 'client') else '0.0.0.0'

        ua = request.headers.get('user-agent', 'unknown')
        device_id = request.headers.get('x-device-id') or request.headers.get('device-id') or request.headers.get('x-device')

        geo = self._query_ip_api(ip) if ip else {}
        is_vpn = False
        isp = geo.get('isp', '') or ''
        org = geo.get('org', '') or ''
        # Heuristics: proxy/hosting fields or known cloud provider strings
        if geo.get('proxy') or geo.get('hosting'):
            is_vpn = True
        lower_isp = isp.lower()
        lower_org = org.lower()
        vpn_keywords = ['vpn', 'proxy', 'hosting', 'digitalocean', 'amazon', 'aws', 'google cloud', 'google', 'cloudflare', 'ovh', 'hetzner', 'microsoft', 'azure']
        if any(k in lower_isp for k in vpn_keywords) or any(k in lower_org for k in vpn_keywords):
            is_vpn = True

        location = None
        if geo:
            country = geo.get('country')
            region = geo.get('regionName')
            city = geo.get('city')
            location = ", ".join([p for p in [city, region, country] if p])

        # Persist activity + update devices
        db = SessionLocal()
        try:
            user_id = getattr(current_user, 'id', None) if current_user is not None else None

            # Update or create device record
            if device_id and user_id:
                dev = db.query(models.UserDevice).filter(models.UserDevice.user_id == user_id, models.UserDevice.device_id == device_id).first()
                if not dev:
                    dev = models.UserDevice(user_id=user_id, device_id=device_id, device_name=ua[:200], is_trusted=False)
                    db.add(dev)
                    db.commit()

            # Log master activity
            act = models.UserActivityMaster(
                user_id=user_id,
                action=action or f"REQUEST {request.method} {request.url.path}",
                ip=ip,
                device=device_id or ua[:200],
                location=location,
                is_vpn=is_vpn,
                timestamp=datetime.now(timezone.utc)
            )
            db.add(act)
            db.commit()

            # If VPN detected -> create security log and alert admin
            if is_vpn:
                slog = models.SecurityLog(user_id=user_id, event_type='vpn_detected', ip_address=ip, description=f'VPN/Proxy suspected ({isp} | {org})')
                db.add(slog)
                db.commit()
                # send telegram alert
                try:
                    admin_chat = getattr(settings, 'ADMIN_CHAT_ID', None)
                    if admin_chat:
                        msg = f"⚠️ VPN/Proxy detected for user_id={user_id} IP={ip} ISP={isp} ORG={org} action={action or request.url.path}"
                        self.telegram.send_alert(admin_chat, msg)
                except Exception:
                    pass
                return {"block": True, "reason": "VPN/Proxy detected"}

            return {"block": False, "reason": "ok"}

        finally:
            db.close()


monitor_service = MonitorService()
