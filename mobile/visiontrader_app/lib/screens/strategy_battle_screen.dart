import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../widgets/common_widgets.dart';

class StrategyBattleScreen extends StatefulWidget {
  const StrategyBattleScreen({Key? key}) : super(key: key);

  @override
  State<StrategyBattleScreen> createState() => _StrategyBattleScreenState();
}

class _StrategyBattleScreenState extends State<StrategyBattleScreen> {
  final ApiService _api = ApiService();
  final AuthService _auth = AuthService();
  bool _isLoading = true;
  String? _error;
  List<Map<String, dynamic>> _battlePairs = [];

  @override
  void initState() {
    super.initState();
    _loadBattleData();
  }

  Future<void> _loadBattleData() async {
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
      final response = await _api.getStrategyComparison(token);
      final pairs = (response['battle_pairs'] as List?)
              ?.map<Map<String, dynamic>>((item) {
            return Map<String, dynamic>.from(item);
          }).toList() ??
          [];
      setState(() {
        _battlePairs = pairs;
      });
    } catch (e) {
      setState(() {
        _error = 'فشل تحميل بيانات معارك الاستراتيجيات.';
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Widget _pairCard(Map<String, dynamic> pair) {
    final left = pair['strategy_a'] as Map<String, dynamic>? ?? {};
    final right = pair['strategy_b'] as Map<String, dynamic>? ?? {};
    final winner = pair['winner'] ?? 'غير محدد';
    return GlassCard(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('مواجهة ${left['name'] ?? '-'} vs ${right['name'] ?? '-'}',
                style:
                    const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _strategyOverview(left),
                _strategyOverview(right),
              ],
            ),
            const SizedBox(height: 12),
            Text('الفائز المتوقع: $winner',
                style: const TextStyle(
                    color: Colors.amber, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }

  Widget _strategyOverview(Map<String, dynamic> data) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(data['name'] ?? '-',
              style: const TextStyle(
                  fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 6),
          Text('ربح: ${data['win_rate']?.toStringAsFixed(1) ?? '-'}%',
              style: const TextStyle(color: Colors.white70)),
          Text('صفقات: ${data['trades'] ?? '-'}',
              style: const TextStyle(color: Colors.white70)),
          Text('مخاطرة: ${data['risk'] ?? '-'}',
              style: const TextStyle(color: Colors.white70)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('معركة الاستراتيجيات')),
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
                      ElevatedButton(
                          onPressed: _loadBattleData,
                          child: const Text('تحديث')),
                      const SizedBox(height: 16),
                      if (_battlePairs.isEmpty)
                        const Center(
                            child: Text('لا توجد مواجهات متاحة حالياً.',
                                style: TextStyle(color: Colors.white70)))
                      else
                        Expanded(
                          child: ListView.separated(
                            itemCount: _battlePairs.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: 12),
                            itemBuilder: (context, index) =>
                                _pairCard(_battlePairs[index]),
                          ),
                        ),
                    ],
                  ),
      ),
    );
  }
}
