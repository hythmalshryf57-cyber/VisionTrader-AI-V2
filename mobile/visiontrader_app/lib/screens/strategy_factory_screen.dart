import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../widgets/common_widgets.dart';

class StrategyFactoryScreen extends StatefulWidget {
  const StrategyFactoryScreen({Key? key}) : super(key: key);

  @override
  State<StrategyFactoryScreen> createState() => _StrategyFactoryScreenState();
}

class _StrategyFactoryScreenState extends State<StrategyFactoryScreen> {
  final ApiService _api = ApiService();
  final AuthService _auth = AuthService();
  bool _isLoading = true;
  String? _error;
  List<Map<String, dynamic>> _strategies = [];

  static const Map<String, int> clusterWeights = {
    'Power Cluster': 40,
    'Geometric Cluster': 30,
    'Momentum Cluster': 30,
  };

  @override
  void initState() {
    super.initState();
    _loadStrategies();
  }

  Future<void> _loadStrategies() async {
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
      final response = await _api.getStrategies(token);
      final list = response.map<Map<String, dynamic>>((item) {
        final Map<String, dynamic> strategy = Map<String, dynamic>.from(item);
        strategy['weight'] = (strategy['weight'] ?? 1.0).toDouble();
        return strategy;
      }).toList();
      setState(() {
        _strategies = list;
      });
    } catch (e) {
      setState(() {
        _error = 'فشل تحميل استراتيجيات النظام.';
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  List<Map<String, dynamic>> _clusterItems(String clusterKey) {
    return _strategies.where((item) => item['cluster'] == clusterKey).toList();
  }

  double _totalWeight(String clusterKey) {
    return _clusterItems(clusterKey)
        .fold(0.0, (sum, item) => sum + (item['weight'] ?? 0.0));
  }

  Future<void> _saveWeight(String name, double weight) async {
    final token = await _auth.getToken();
    if (token == null) return;
    await _api.updateStrategyWeight(token, name, weight);
    ScaffoldMessenger.of(context)
        .showSnackBar(const SnackBar(content: Text('تم حفظ وزن الاستراتيجية')));
  }

  Color _weightColor(double value, double original) {
    if (value > original) return Colors.greenAccent;
    if (value < original) return Colors.redAccent;
    return Colors.white;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('مصنع الاستراتيجيات')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(
                    child: Text(_error!,
                        style: const TextStyle(color: Colors.redAccent)))
                : DefaultTabController(
                    length: 3,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        TabBar(
                          tabs: clusterWeights.keys
                              .map((name) => Tab(text: name))
                              .toList(),
                        ),
                        const SizedBox(height: 16),
                        Expanded(
                          child: TabBarView(
                            children: clusterWeights.keys.map((clusterName) {
                              final items = _clusterItems(clusterName);
                              final target = clusterWeights[clusterName] ?? 0;

                              return SingleChildScrollView(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    GlassCard(
                                      child: Padding(
                                        padding: const EdgeInsets.all(16.0),
                                        child: Row(
                                          mainAxisAlignment:
                                              MainAxisAlignment.spaceBetween,
                                          children: [
                                            Text(
                                                'الوزن الحالي: ${_totalWeight(clusterName).toStringAsFixed(1)}%',
                                                style: const TextStyle(
                                                    color: Colors.white)),
                                            Text('الهدف: $target%',
                                                style: const TextStyle(
                                                    color: Colors.white70)),
                                          ],
                                        ),
                                      ),
                                    ),
                                    const SizedBox(height: 16),
                                    if (items.isEmpty)
                                      const Text(
                                          'لا توجد استراتيجيات في هذا العنقود.',
                                          style:
                                              TextStyle(color: Colors.white70))
                                    else
                                      ...items.map((strategy) {
                                        final originalWeight =
                                            (strategy['weight'] ?? 1.0)
                                                .toDouble();
                                        return GlassCard(
                                          child: Padding(
                                            padding: const EdgeInsets.all(16.0),
                                            child: Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.start,
                                              children: [
                                                Text(
                                                    strategy['strategy_name'] ??
                                                        strategy['name'] ??
                                                        'استراتيجية',
                                                    style: const TextStyle(
                                                        fontSize: 16,
                                                        fontWeight:
                                                            FontWeight.bold)),
                                                const SizedBox(height: 8),
                                                Row(
                                                  mainAxisAlignment:
                                                      MainAxisAlignment
                                                          .spaceBetween,
                                                  children: [
                                                    Text(
                                                        'الوزن: ${originalWeight.toStringAsFixed(1)}',
                                                        style: TextStyle(
                                                            color: _weightColor(
                                                                originalWeight,
                                                                originalWeight))),
                                                    Text(
                                                        'نجاح: ${strategy['win_rate']?.toStringAsFixed(1) ?? '0.0'}%',
                                                        style: const TextStyle(
                                                            color: Colors
                                                                .white70)),
                                                  ],
                                                ),
                                                Slider(
                                                  value: originalWeight,
                                                  min: 0.1,
                                                  max: 3.0,
                                                  divisions: 29,
                                                  label: originalWeight
                                                      .toStringAsFixed(1),
                                                  onChanged: (value) {
                                                    setState(() {
                                                      strategy['weight'] =
                                                          value;
                                                    });
                                                  },
                                                ),
                                                Text(
                                                    'عدد الصفقات: ${strategy['total_trades'] ?? '-'}',
                                                    style: const TextStyle(
                                                        color: Colors.white70)),
                                                const SizedBox(height: 8),
                                                ElevatedButton(
                                                  onPressed: () => _saveWeight(
                                                      strategy[
                                                              'strategy_name'] ??
                                                          strategy['name'] ??
                                                          '',
                                                      strategy['weight']
                                                              ?.toDouble() ??
                                                          originalWeight),
                                                  child: const Text('حفظ'),
                                                ),
                                              ],
                                            ),
                                          ),
                                        );
                                      }).toList(),
                                    const SizedBox(height: 16),
                                    ElevatedButton(
                                      onPressed: () async {
                                        for (final strategy in items) {
                                          await _saveWeight(
                                              strategy['strategy_name'] ??
                                                  strategy['name'] ??
                                                  '',
                                              strategy['weight']?.toDouble() ??
                                                  1.0);
                                        }
                                      },
                                      child: const Text('حفظ الكل'),
                                    ),
                                  ],
                                ),
                              );
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
