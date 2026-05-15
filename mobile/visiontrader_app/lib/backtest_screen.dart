import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class BacktestScreen extends StatefulWidget {
  @override
  _BacktestScreenState createState() => _BacktestScreenState();
}

class _BacktestScreenState extends State<BacktestScreen> {
  String? selectedMarket;
  String? selectedTimeframe;
  DateTime? startDate;
  DateTime? endDate;
  Map<String, dynamic>? results;
  bool isLoading = false;

  final List<String> markets = ['ذهب', 'عملات', 'مؤشرات', 'نفط'];
  final List<String> timeframes = ['سكالبينج', 'يومي', 'سوينغ', 'استثماري'];

  Future<void> runBacktest() async {
    if (selectedMarket == null ||
        selectedTimeframe == null ||
        startDate == null ||
        endDate == null) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('يرجى ملء جميع الحقول')));
      return;
    }

    setState(() {
      isLoading = true;
    });

    var requestBody = {
      'market': selectedMarket,
      'timeframe': selectedTimeframe,
      'startDate': startDate!.toIso8601String(),
      'endDate': endDate!.toIso8601String(),
    };

    try {
      var response = await http.post(
        Uri.parse('https://your-api-endpoint.com/api/backtest'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(requestBody),
      );
      if (response.statusCode == 200) {
        setState(() {
          results = json.decode(response.body);
          isLoading = false;
        });
      } else {
        setState(() {
          isLoading = false;
        });
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('فشل في تشغيل الاختبار')));
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Backtest')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            DropdownButton<String>(
              hint: Text('اختر السوق'),
              value: selectedMarket,
              onChanged: (String? newValue) {
                setState(() {
                  selectedMarket = newValue;
                });
              },
              items: markets.map<DropdownMenuItem<String>>((String value) {
                return DropdownMenuItem<String>(
                  value: value,
                  child: Text(value),
                );
              }).toList(),
            ),
            SizedBox(height: 16),
            DropdownButton<String>(
              hint: Text('اختر الفريم'),
              value: selectedTimeframe,
              onChanged: (String? newValue) {
                setState(() {
                  selectedTimeframe = newValue;
                });
              },
              items: timeframes.map<DropdownMenuItem<String>>((String value) {
                return DropdownMenuItem<String>(
                  value: value,
                  child: Text(value),
                );
              }).toList(),
            ),
            SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: TextButton(
                    onPressed: () async {
                      startDate = await showDatePicker(
                        context: context,
                        initialDate: DateTime.now(),
                        firstDate: DateTime(2020),
                        lastDate: DateTime.now(),
                      );
                      setState(() {});
                    },
                    child: Text(
                      startDate == null
                          ? 'تاريخ البداية'
                          : startDate!.toString().split(' ')[0],
                    ),
                  ),
                ),
                SizedBox(width: 16),
                Expanded(
                  child: TextButton(
                    onPressed: () async {
                      endDate = await showDatePicker(
                        context: context,
                        initialDate: DateTime.now(),
                        firstDate: DateTime(2020),
                        lastDate: DateTime.now(),
                      );
                      setState(() {});
                    },
                    child: Text(
                      endDate == null
                          ? 'تاريخ النهاية'
                          : endDate!.toString().split(' ')[0],
                    ),
                  ),
                ),
              ],
            ),
            SizedBox(height: 16),
            isLoading
                ? CircularProgressIndicator()
                : ElevatedButton(
                    onPressed: runBacktest,
                    child: Text('تشغيل الاختبار'),
                  ),
            SizedBox(height: 16),
            if (results != null)
              Expanded(
                child: ListView(
                  children: [
                    Text('نسبة النجاح: ${results!['successRate']}%'),
                    Text('الربح: ${results!['profit']}'),
                    Text('الخسارة: ${results!['loss']}'),
                    Text('Sharpe Ratio: ${results!['sharpeRatio']}'),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
