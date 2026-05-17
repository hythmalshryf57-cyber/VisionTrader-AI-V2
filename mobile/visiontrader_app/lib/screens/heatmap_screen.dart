import 'dart:async';

import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../widgets/common_widgets.dart';

class HeatmapScreen extends StatefulWidget {
  const HeatmapScreen({Key? key}) : super(key: key);

  @override
  State<HeatmapScreen> createState() => _HeatmapScreenState();
}

class _HeatmapScreenState extends State<HeatmapScreen> {
  final ApiService _api = ApiService();
  final AuthService _auth = AuthService();
  bool _isLoading = true;
  String? _error;
  List<Map<String, dynamic>> _markets = [];
  Timer? _refreshTimer;

  static const List<String> _marketSymbols = [
    'XAUUSD',
    'BTCUSDT',
    'ETHUSDT',
    'EURUSD',
    'GBPUSD',
    'USDJPY',
    'XAGUSD',
    'US30',
    'NAS100',
    'SPX500',
  ];

  @override
  void initState() {
    super.initState();
    _loadHeatmap();
    _refreshTimer =
        Timer.periodic(const Duration(seconds: 30), (_) => _loadHeatmap());
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadHeatmap() async {
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
      final response = await _api.compareMarkets(token, _marketSymbols);
      if (response['markets'] is List) {
        final items =
            (response['markets'] as List).map<Map<String, dynamic>>((item) {
          return Map<String, dynamic>.from(item);
        }).toList();
        setState(() => _markets = items);
      } else {
        _generateFallback();
      }
    } catch (e) {
      _generateFallback();
      setState(() {
        _error = 'فشل تحميل بيانات خريطة الحرارة. سيتم عرض بيانات مؤقتة.';
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _generateFallback() {
    setState(() {
      _markets = _marketSymbols.map((symbol) {
        final index = _marketSymbols.indexOf(symbol);
        final direction = index % 3 == 0
            ? 'شراء'
            : index % 3 == 1
                ? 'بيع'
                : 'انتظار';
        return {
          'market': symbol,
          'recommendation': direction,
          'confidence': 60 + (index * 3),
        };
      }).toList();
    });
  }

  Color _tileColor(String recommendation, int confidence) {
    if (recommendation == 'شراء') {
      return Colors.green.withOpacity((confidence.clamp(50, 100) / 100));
    }
    if (recommendation == 'بيع') {
      return Colors.red.withOpacity((confidence.clamp(50, 100) / 100));
    }
    return Colors.grey.withOpacity((confidence.clamp(30, 80) / 100));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('خريطة حرارة الأسواق'),
        actions: [
          IconButton(onPressed: _loadHeatmap, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : Column(
                children: [
                  if (_error != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12.0),
                      child: Text(_error!,
                          style: const TextStyle(color: Colors.amber)),
                    ),
                  Expanded(
                    child: GridView.count(
                      crossAxisCount: 2,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      childAspectRatio: 1.15,
                      children: _markets.map((market) {
                        final confidence = (market['confidence'] ?? 50).toInt();
                        final recommendation =
                            market['recommendation'] ?? 'انتظار';
                        return GestureDetector(
                          onTap: () {
                            Navigator.pushNamed(
                              context,
                              '/result',
                              arguments: {
                                'market': market['market'],
                                'recommendation': recommendation,
                                'confidence': confidence,
                                'entry': '-',
                                'stop': '-',
                                'targets': '-',
                                'rrr': '-',
                                'strategies': [
                                  {
                                    'name': 'Heatmap',
                                    'logic': 'تم التوجيه من خريطة الحرارة'
                                  }
                                ],
                              },
                            );
                          },
                          child: GlassCard(
                            child: Container(
                              decoration: BoxDecoration(
                                color: _tileColor(recommendation, confidence),
                                borderRadius: BorderRadius.circular(16),
                              ),
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(market['market'] ?? '-',
                                      style: const TextStyle(
                                          fontSize: 18,
                                          fontWeight: FontWeight.bold,
                                          color: Colors.white)),
                                  Text(recommendation,
                                      style: const TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.bold)),
                                  Text('ثقة $confidence%',
                                      style: const TextStyle(
                                          color: Colors.white70)),
                                ],
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
