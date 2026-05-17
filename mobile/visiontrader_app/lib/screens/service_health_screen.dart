import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../widgets/common_widgets.dart';

class ServiceHealthScreen extends StatefulWidget {
  const ServiceHealthScreen({Key? key}) : super(key: key);

  @override
  State<ServiceHealthScreen> createState() => _ServiceHealthScreenState();
}

class _ServiceHealthScreenState extends State<ServiceHealthScreen> {
  final ApiService _api = ApiService();
  final AuthService _auth = AuthService();
  bool _isLoading = true;
  String? _error;
  Map<String, dynamic> _pulse = {};

  @override
  void initState() {
    super.initState();
    _refreshPulse();
  }

  Future<void> _refreshPulse() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    final token = await _auth.getToken();
    if (token == null) {
      setState(() {
        _error = 'يرجى تسجيل الدخول أولاً.';
        _isLoading = false;
      });
      return;
    }

    try {
      final pulse = await _api.getSystemPulse(token);
      setState(() => _pulse = pulse);
    } catch (e) {
      setState(() {
        _error = 'فشل جلب حالة الخدمات. تحقق من الشبكة.';
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Widget _statusItem(String title, bool active) {
    return GlassCard(
      child: ListTile(
        leading: Icon(
          active ? Icons.circle : Icons.circle_outlined,
          color: active ? Colors.greenAccent : Colors.redAccent,
        ),
        title: Text(title, style: const TextStyle(color: Colors.white)),
        trailing: Text(active ? 'متصل' : 'غير متصل',
            style: TextStyle(
                color: active ? Colors.greenAccent : Colors.redAccent)),
      ),
    );
  }

  bool _isConnected(String? status) {
    final normalized = status?.toLowerCase() ?? '';
    return normalized.contains('online') ||
        normalized.contains('connected') ||
        normalized.contains('ok') ||
        normalized.contains('متصل');
  }

  @override
  Widget build(BuildContext context) {
    final healthDetails = _pulse['health_details'] as Map<String, dynamic>?;
    final external =
        healthDetails?['external_api_state'] as Map<String, dynamic>?;
    final lastRefresh = _pulse['refresh_time'] ?? '-';

    return Scaffold(
      appBar: AppBar(title: const Text('صحة الخدمات')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(
                    child: Text(_error!,
                        style: const TextStyle(color: Colors.redAccent)))
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('تحديث الحالة',
                              style: TextStyle(
                                  fontSize: 18, fontWeight: FontWeight.bold)),
                          ElevatedButton(
                              onPressed: _refreshPulse,
                              child: const Text('تحديث')),
                        ],
                      ),
                      const SizedBox(height: 16),
                      if (external != null) ...[
                        _statusItem('Binance',
                            _isConnected(external['binance']?.toString())),
                        const SizedBox(height: 12),
                        _statusItem('TradingView',
                            _isConnected(external['tradingview']?.toString())),
                        const SizedBox(height: 12),
                        _statusItem('Telegram',
                            _isConnected(external['telegram']?.toString())),
                        const SizedBox(height: 12),
                        _statusItem('Supabase',
                            _isConnected(external['supabase']?.toString())),
                        const SizedBox(height: 12),
                        _statusItem('Redis',
                            _isConnected(external['redis']?.toString())),
                      ] else
                        const Text('لا توجد بيانات حالة متاحة حالياً.',
                            style: TextStyle(color: Colors.white70)),
                      const SizedBox(height: 16),
                      GlassCard(
                        child: ListTile(
                          title: const Text('آخر تحديث',
                              style: TextStyle(color: Colors.white70)),
                          subtitle: Text(lastRefresh,
                              style: const TextStyle(color: Colors.white)),
                        ),
                      ),
                    ],
                  ),
      ),
    );
  }
}
