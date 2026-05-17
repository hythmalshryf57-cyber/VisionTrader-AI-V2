import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../widgets/common_widgets.dart';

class AdminScreen extends StatefulWidget {
  const AdminScreen({Key? key}) : super(key: key);

  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> {
  final ApiService _api = ApiService();
  final AuthService _auth = AuthService();
  bool _isLoading = true;
  String? _error;
  List<dynamic> _users = [];
  List<dynamic> _inviteCodes = [];
  Map<String, dynamic> _systemHealth = {};

  @override
  void initState() {
    super.initState();
    _loadAdminData();
  }

  Future<void> _loadAdminData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    final token = await _auth.getToken();
    if (token == null || token.isEmpty) {
      setState(() {
        _error = 'يرجى تسجيل الدخول أولاً.';
        _isLoading = false;
      });
      return;
    }

    try {
      final users = await _api.getAdminUsers(token);
      final invites = await _api.getAdminInviteCodes(token);
      final health = await _api.getSystemHealth(token);
      setState(() {
        _users = users;
        _inviteCodes = invites;
        _systemHealth = health;
      });
    } catch (e) {
      setState(() {
        _error = 'فشل تحميل بيانات الأدمن. تأكد من اتصالك بالإنترنت.';
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _toggleFreeze(dynamic user) async {
    final token = await _auth.getToken();
    if (token == null) return;
    final userId = user['id']?.toString() ?? '';
    final active = user['active'] == true;
    await _api.freezeUser(token, userId, !active);
    await _loadAdminData();
  }

  Future<void> _killSession(dynamic user) async {
    final token = await _auth.getToken();
    if (token == null) return;
    final userId = user['id']?.toString() ?? '';
    await _api.killUserSession(token, userId);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('تم إنهاء الجلسة.')),
    );
  }

  Future<void> _createInviteCode() async {
    final codeController = TextEditingController();
    final usesController = TextEditingController(text: '5');
    final expiryController = TextEditingController(
        text: DateTime.now()
            .add(const Duration(days: 30))
            .toIso8601String()
            .split('T')
            .first);

    final result = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1F2130),
          title: const Text('إنشاء رمز دعوة جديد'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: codeController,
                decoration: const InputDecoration(labelText: 'الكود'),
              ),
              const SizedBox(height: 12),
              TextField(
                keyboardType: TextInputType.number,
                controller: usesController,
                decoration:
                    const InputDecoration(labelText: 'الحد الأقصى للاستخدام'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: expiryController,
                decoration: const InputDecoration(
                    labelText: 'تاريخ الانتهاء (YYYY-MM-DD)'),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('إلغاء'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('إنشاء'),
            ),
          ],
        );
      },
    );

    if (result != true) return;
    final token = await _auth.getToken();
    if (token == null) return;

    try {
      await _api.createInviteCode(
        token,
        codeController.text.trim(),
        int.tryParse(usesController.text) ?? 1,
        expiryController.text.trim(),
      );
      await _loadAdminData();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('تم إنشاء رمز الدعوة بنجاح.')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('فشل إنشاء رمز الدعوة.')),
      );
    }
  }

  Widget _metricCard(String title, String value, {Color color = Colors.white}) {
    return Expanded(
      child: GlassCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(color: Colors.white70)),
            const SizedBox(height: 8),
            Text(value,
                style: TextStyle(
                    color: color, fontWeight: FontWeight.bold, fontSize: 20)),
          ],
        ),
      ),
    );
  }

  Widget _statusChip(bool value) {
    return Chip(
      backgroundColor: value ? Colors.green : Colors.red,
      label: Text(value ? 'متصل' : 'غير متصل',
          style: const TextStyle(color: Colors.white)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('لوحة الأدمن')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(
                    child: Text(_error!,
                        style: const TextStyle(color: Colors.redAccent)))
                : SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 12),
                        Text('SOC Dashboard',
                            style: Theme.of(context).textTheme.headline6),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            _metricCard('Total Users',
                                '${_systemHealth['total_users'] ?? '-'}',
                                color: Colors.amber),
                            const SizedBox(width: 12),
                            _metricCard('Active Today',
                                '${_systemHealth['active_today'] ?? '-'}'),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            _metricCard('Total Analyses',
                                '${_systemHealth['total_analyses'] ?? '-'}'),
                            const SizedBox(width: 12),
                            _metricCard('API Calls',
                                '${_systemHealth['api_calls'] ?? '-'}'),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            _metricCard('Errors (24h)',
                                '${_systemHealth['errors_24h'] ?? '-'}',
                                color: Colors.redAccent),
                            const SizedBox(width: 12),
                            _metricCard('Blocked IPs',
                                '${_systemHealth['blocked_ips'] ?? '-'}'),
                          ],
                        ),
                        const SizedBox(height: 24),
                        Text('إحصائيات النظام',
                            style: Theme.of(context).textTheme.headline6),
                        const SizedBox(height: 12),
                        GlassCard(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('CPU: ${_systemHealth['cpu'] ?? '-'}'),
                              Text('RAM: ${_systemHealth['ram'] ?? '-'}'),
                              Text('Uptime: ${_systemHealth['uptime'] ?? '-'}'),
                              Text(
                                  'Request Count: ${_systemHealth['request_count'] ?? '-'}'),
                              Text(
                                  'Daily Requests: ${_systemHealth['daily_requests'] ?? '-'}'),
                              const SizedBox(height: 8),
                              Text(
                                  'آخر خطأ: ${_systemHealth['last_error'] ?? 'لا يوجد'}'),
                            ],
                          ),
                        ),
                        const SizedBox(height: 24),
                        Text('قائمة المستخدمين',
                            style: Theme.of(context).textTheme.headline6),
                        const SizedBox(height: 12),
                        SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: DataTable(
                            columns: const [
                              DataColumn(label: Text('ID')),
                              DataColumn(label: Text('Email')),
                              DataColumn(label: Text('Active')),
                              DataColumn(label: Text('Admin')),
                              DataColumn(label: Text('Trial End')),
                              DataColumn(label: Text('Created')),
                              DataColumn(label: Text('Actions')),
                            ],
                            rows: _users.map((user) {
                              final active = user['active'] == true;
                              return DataRow(cells: [
                                DataCell(Text(user['id']?.toString() ?? '-')),
                                DataCell(Text(user['email'] ?? '-')),
                                DataCell(_statusChip(active)),
                                DataCell(_statusChip(user['is_admin'] == true)),
                                DataCell(Text(user['trial_end'] ?? '-')),
                                DataCell(Text(user['created_at'] ?? '-')),
                                DataCell(Row(
                                  children: [
                                    TextButton(
                                      onPressed: () => _toggleFreeze(user),
                                      child:
                                          Text(active ? 'Freeze' : 'Unfreeze'),
                                    ),
                                    TextButton(
                                      onPressed: () => _killSession(user),
                                      child: const Text('Kill'),
                                    ),
                                  ],
                                )),
                              ]);
                            }).toList(),
                          ),
                        ),
                        const SizedBox(height: 24),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text('رموز الدعوة',
                                style: Theme.of(context).textTheme.headline6),
                            ElevatedButton(
                                onPressed: _createInviteCode,
                                child: const Text('إنشاء رمز جديد')),
                          ],
                        ),
                        const SizedBox(height: 12),
                        SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: DataTable(
                            columns: const [
                              DataColumn(label: Text('الكود')),
                              DataColumn(label: Text('استخدامات')),
                              DataColumn(label: Text('Max Uses')),
                              DataColumn(label: Text('Expiry')),
                              DataColumn(label: Text('Active')),
                              DataColumn(label: Text('Action')),
                            ],
                            rows: _inviteCodes.map((invite) {
                              final active = invite['active'] == true;
                              return DataRow(cells: [
                                DataCell(Text(invite['code'] ?? '-')),
                                DataCell(Text('${invite['uses'] ?? 0}')),
                                DataCell(Text('${invite['max_uses'] ?? '-'}')),
                                DataCell(Text(invite['expiry_date'] ?? '-')),
                                DataCell(_statusChip(active)),
                                DataCell(TextButton(
                                  onPressed: () async {
                                    final token = await _auth.getToken();
                                    if (token == null) return;
                                    await _api.toggleInviteCode(
                                        token, invite['code'] ?? '', !active);
                                    await _loadAdminData();
                                  },
                                  child: Text(active ? 'Disable' : 'Enable'),
                                )),
                              ]);
                            }).toList(),
                          ),
                        ),
                      ],
                    ),
                  ),
      ),
    );
  }
}
