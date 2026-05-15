import 'package:flutter/material.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';

class ResultScreen extends StatelessWidget {
  final Map<String, dynamic> result;

  ResultScreen({required this.result});

  void exportToPDF() async {
    final pdf = pw.Document();

    pdf.addPage(
      pw.Page(
        build: (pw.Context context) {
          return pw.Column(
            children: [
              pw.Text('نتيجة التحليل', style: pw.TextStyle(fontSize: 24)),
              pw.SizedBox(height: 20),
              pw.Text('التوصية: ${result['recommendation']}'),
              pw.Text('الثقة: ${result['confidence']}'),
              pw.Text('الدخول: ${result['entry']}'),
              pw.Text('الوقف: ${result['stop']}'),
              pw.Text('الأهداف: ${result['targets']}'),
              pw.Text('RRR: ${result['rrr']}'),
              pw.SizedBox(height: 20),
              pw.Text('أفضل 3 استراتيجيات:'),
              for (var strategy in result['strategies'])
                pw.Text('${strategy['name']}: ${strategy['logic']}'),
            ],
          );
        },
      ),
    );

    await Printing.layoutPdf(
      onLayout: (PdfPageFormat format) async => pdf.save(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('نتيجة التحليل')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'التوصية: ${result['recommendation']}',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text('الثقة: ${result['confidence']}'),
                    Text('الدخول: ${result['entry']}'),
                    Text('الوقف: ${result['stop']}'),
                    Text('الأهداف: ${result['targets']}'),
                    Text('RRR: ${result['rrr']}'),
                  ],
                ),
              ),
            ),
            SizedBox(height: 16),
            Text(
              'أفضل 3 استراتيجيات:',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            for (var strategy in result['strategies'])
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(8.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        strategy['name'],
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      Text(strategy['logic']),
                    ],
                  ),
                ),
              ),
            SizedBox(height: 16),
            ElevatedButton(onPressed: exportToPDF, child: Text('تصدير PDF')),
          ],
        ),
      ),
    );
  }
}
