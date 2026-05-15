import 'package:flutter/material.dart';
import '../widgets/common_widgets.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _isLoadingStats = true;
  bool _isLoadingAlerts = true;
  List<Map<String, dynamic>> _alerts = [];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    // Simulate loading
    await Future.delayed(const Duration(seconds: 2));
    setState(() {
      _isLoadingStats = false;
      _isLoadingAlerts = false;
      _alerts = [
        {'market': 'BTCUSDT', 'recommendation': 'شراء', 'confidence': 95},
        {'market': 'EURUSD', 'recommendation': 'بيع', 'confidence': 78},
      ];
    });
  }

  Widget _sidebar(BuildContext context) {
    return Container(
      width: 200,
      color: const Color(0xFF23243A),
      child: ListView(
        children: [
          const DrawerHeader(
            child: Text(
              'VisionTrader',
              style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold),
            ),
          ),
          _sidebarItem(context, Icons.analytics, 'تحليل جديد', '/upload'),
          _sidebarItem(context, Icons.history, 'سجل', '/history'),
          _sidebarItem(context, Icons.calendar_today, 'تقويم', '/calendar'),
          _sidebarItem(context, Icons.settings, 'إعدادات', '/settings'),
          _sidebarItem(context, Icons.science, 'Backtest', '/backtest'),
        ],
      ),
    );
  }

  Widget _sidebarItem(
    BuildContext context,
    IconData icon,
    String title,
    String route,
  ) {
    return ListTile(
      leading: Icon(icon, color: Colors.white70),
      title: Text(title, style: const TextStyle(color: Colors.white)),
      onTap: () => Navigator.pushNamed(context, route),
    );
  }

  Widget _newsTicker() {
    return Container(
      height: 40,
      margin: const EdgeInsets.symmetric(vertical: 16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.15), width: 0.5),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              color: Colors.amber.withOpacity(0.2),
              child: const Text(
                'أخبار',
                style: TextStyle(color: Colors.amber, fontSize: 12, fontWeight: FontWeight.bold),
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _tickerItem(Icons.trending_up, 'BTCUSDT: شراء بثقة 95%'),
                    _tickerItem(Icons.calendar_today, 'أحداث اقتصادية قادمة'),
                    _tickerItem(Icons.water, 'آخر صفقة حوت: 500k$'),
                    _tickerItem(Icons.trending_down, 'EURUSD: بيع بثقة 78%'),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _tickerItem(IconData icon, String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          Icon(icon, size: 16, color: Colors.white70),
          const SizedBox(width: 8),
          Text(text, style: const TextStyle(color: Colors.white, fontSize: 14)),
        ],
      ),
    );
  }

  Widget _quickStats() {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'إحصائيات سريعة',
            style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              _statItem('الصفقات', _isLoadingStats ? null : '120'),
              _statItem('الربح', _isLoadingStats ? null : '15%'),
              _statItem('الخسارة', _isLoadingStats ? null : '5%'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _statItem(String label, String? value) {
    return Expanded(
      child: Column(
        children: [
          value != null
              ? Text(
                  value,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                )
              : const SkeletonLoader(width: 50, height: 20),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(color: Colors.white70)),
        ],
      ),
    );
  }

  Widget _alerts() {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'التنبيهات',
            style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          if (_isLoadingAlerts)
            const SkeletonLoader(height: 60)
          else if (_alerts.isEmpty)
            const Text(
              'لا توجد تنبيهات حالياً',
              style: TextStyle(color: Colors.white70),
            )
          else
            ..._alerts.map((alert) => GoldenGlow(
                  isGlowing: (alert['confidence'] as int) >= 90,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(8),
                      border: Border(
                        left: BorderSide(
                          color: alert['recommendation'] == 'شراء' ? Colors.green : Colors.red,
                          width: 3,
                        ),
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          alert['recommendation'] == 'شراء' ? Icons.arrow_upward : Icons.arrow_downward,
                          color: alert['recommendation'] == 'شراء' ? Colors.green : Colors.red,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${alert['market']}: ${alert['recommendation']} قوي',
                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                              ),
                              Text(
                                'ثقة ${alert['confidence']}%',
                                style: const TextStyle(color: Colors.white70, fontSize: 12),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                )),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF181A20),
      body: Row(
        children: [
          _sidebar(context),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _newsTicker(),
                  _quickStats(),
                  const SizedBox(height: 32),
                  _alerts(),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
