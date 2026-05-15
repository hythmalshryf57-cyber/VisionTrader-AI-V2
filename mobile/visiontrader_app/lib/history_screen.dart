import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'result_screen.dart';
import 'widgets/common_widgets.dart';

class HistoryScreen extends StatefulWidget {
  @override
  _HistoryScreenState createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<dynamic> history = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    fetchHistory();
  }

  Future<void> fetchHistory() async {
    setState(() {
      isLoading = true;
    });
    try {
      var response = await http.get(
        Uri.parse('https://your-api-endpoint.com/api/analysis/history'),
      );
      if (response.statusCode == 200) {
        setState(() {
          history = json.decode(response.body);
          isLoading = false;
        });
      } else {
        setState(() {
          isLoading = false;
        });
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('فشل في جلب التاريخ')));
      }
    } catch (e) {
      setState(() {
        isLoading = false;
      });
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('خطأ في الاتصال')));
    }
  }

  Color getRecommendationColor(String recommendation) {
    switch (recommendation.toLowerCase()) {
      case 'buy':
        return Colors.green;
      case 'sell':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('التاريخ')),
      body: RefreshIndicator(
        onRefresh: fetchHistory,
        child: isLoading
            ? ListView.builder(
                itemCount: 5,
                itemBuilder: (context, index) => const Padding(
                  padding: EdgeInsets.all(8.0),
                  child: GlassCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SkeletonLoader(width: 200, height: 20),
                        SizedBox(height: 8),
                        SkeletonLoader(width: 150, height: 16),
                      ],
                    ),
                  ),
                ),
              )
            : ListView.builder(
                itemCount: history.length,
                itemBuilder: (context, index) {
                  var item = history[index];
                  return Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: GlassCard(
                      child: ListTile(
                        title: Text(
                          '${item['date']} - ${item['market']}',
                          style: const TextStyle(
                              color: Colors.white, fontWeight: FontWeight.bold),
                        ),
                        subtitle: Text(
                          'الثقة: ${item['confidence']}%',
                          style: const TextStyle(color: Colors.white70),
                        ),
                        trailing: GoldenGlow(
                          isGlowing: int.tryParse(
                                  item['confidence']?.toString() ?? '0') ??
                              0 >= 90,
                          child: Text(
                            item['recommendation'],
                            style: TextStyle(
                              color: getRecommendationColor(
                                  item['recommendation']),
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => ResultScreen(result: item),
                            ),
                          );
                        },
                      ),
                    ),
                  );
                },
              ),
      ),
    );
  }
}
