import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'widgets/common_widgets.dart';

class CalendarScreen extends StatefulWidget {
  @override
  _CalendarScreenState createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  List<dynamic> events = [];
  String? selectedImportance;
  String? selectedCurrency;
  bool isLoading = true;

  final List<String> importances = ['عالية', 'متوسطة', 'منخفضة'];
  final List<String> currencies = ['USD', 'EUR', 'GBP', 'JPY']; // Example

  @override
  void initState() {
    super.initState();
    fetchEvents();
  }

  Future<void> fetchEvents() async {
    setState(() {
      isLoading = true;
    });
    try {
      var response = await http.get(
        Uri.parse('https://your-api-endpoint.com/api/calendar/events'),
      );
      if (response.statusCode == 200) {
        setState(() {
          events = json.decode(response.body);
          isLoading = false;
        });
      } else {
        setState(() {
          isLoading = false;
        });
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('فشل في جلب الأحداث')));
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

  List<dynamic> getFilteredEvents() {
    return events.where((event) {
      bool importanceMatch = selectedImportance == null ||
          event['importance'] == selectedImportance;
      bool currencyMatch =
          selectedCurrency == null || event['currency'] == selectedCurrency;
      return importanceMatch && currencyMatch;
    }).toList();
  }

  Color getImportanceColor(String importance) {
    switch (importance) {
      case 'عالية':
        return Colors.red;
      case 'متوسطة':
        return Colors.orange;
      case 'منخفضة':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('التقويم')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                Expanded(
                  child: DropdownButton<String>(
                    hint: Text('فلترة الأهمية'),
                    value: selectedImportance,
                    onChanged: (String? newValue) {
                      setState(() {
                        selectedImportance = newValue;
                      });
                    },
                    items: importances.map<DropdownMenuItem<String>>((
                      String value,
                    ) {
                      return DropdownMenuItem<String>(
                        value: value,
                        child: Text(value),
                      );
                    }).toList(),
                  ),
                ),
                SizedBox(width: 16),
                Expanded(
                  child: DropdownButton<String>(
                    hint: Text('فلترة العملة'),
                    value: selectedCurrency,
                    onChanged: (String? newValue) {
                      setState(() {
                        selectedCurrency = newValue;
                      });
                    },
                    items: currencies.map<DropdownMenuItem<String>>((
                      String value,
                    ) {
                      return DropdownMenuItem<String>(
                        value: value,
                        child: Text(value),
                      );
                    }).toList(),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: isLoading
                ? ListView.builder(
                    itemCount: 5,
                    itemBuilder: (context, index) => const Padding(
                      padding: EdgeInsets.all(8.0),
                      child: GlassCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SkeletonLoader(width: 250, height: 20),
                            SizedBox(height: 8),
                            SkeletonLoader(width: 150, height: 16),
                          ],
                        ),
                      ),
                    ),
                  )
                : ListView.builder(
                    itemCount: getFilteredEvents().length,
                    itemBuilder: (context, index) {
                      var event = getFilteredEvents()[index];
                      return Padding(
                        padding: const EdgeInsets.all(8.0),
                        child: GlassCard(
                          child: ListTile(
                            title: Text(
                              event['title'],
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold),
                            ),
                            subtitle: Text(
                              '${event['date']} - ${event['currency']}',
                              style: const TextStyle(color: Colors.white70),
                            ),
                            trailing: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: getImportanceColor(event['importance'])
                                    .withOpacity(0.2),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Text(
                                event['importance'],
                                style: TextStyle(
                                  color:
                                      getImportanceColor(event['importance']),
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
