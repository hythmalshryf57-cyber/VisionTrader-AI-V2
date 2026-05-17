import 'package:flutter/material.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';

class ResultScreen extends StatelessWidget {
  final Map<String, dynamic> result;

  ResultScreen({required this.result});

  void exportToPDF() async {
    final pdf = pw.Document();
    final strategies = result['strategies'] is List
        ? result['strategies'] as List
        : <dynamic>[];
    final recommendation = result['recommendation'] ?? 'غير محدد';
    final confidence = result['confidence']?.toString() ?? '-';
    final entry = result['entry'] ?? '-';
    final stop = result['stop'] ?? '-';
    final targets = result['targets'] ?? '-';
    final rrr = result['rrr'] ?? '-';
    final market = result['market'] ?? 'سوق غير معروف';

    pdf.addPage(
      pw.Page(
        build: (pw.Context context) {
          return pw.Column(
            crossAxisAlignment: pw.CrossAxisAlignment.start,
            children: [
              pw.Text('نتيجة التحليل - $market',
                  style: pw.TextStyle(
                      fontSize: 24, fontWeight: pw.FontWeight.bold)),
              pw.SizedBox(height: 20),
              pw.Text('التوصية: $recommendation'),
              pw.Text('الثقة: $confidence'),
              pw.Text('الدخول: $entry'),
              pw.Text('الوقف: $stop'),
              pw.Text('الأهداف: $targets'),
              pw.Text('RRR: $rrr'),
              pw.SizedBox(height: 20),
              pw.Text('أفضل استراتيجيات:'),
              ...strategies.map((strategy) {
                final name = strategy['name'] ?? 'استراتيجية غير معروفة';
                final description =
                    strategy['logic'] ?? strategy['description'] ?? '-';
                return pw.Text('$name: $description');
              }).toList(),
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
    final recommendation = result['recommendation'] ?? 'غير محدد';
    final confidence = result['confidence']?.toString() ?? '-';
    final entry = result['entry'] ?? '-';
    final stop = result['stop'] ?? '-';
    final targets = result['targets'] ?? '-';
    final rrr = result['rrr'] ?? '-';
    final market = result['market'] ?? 'سوق غير معروف';
    final strategies = result['strategies'] is List
        ? result['strategies'] as List
        : <dynamic>[];

    return Scaffold(
      appBar: AppBar(title: Text('نتيجة التحليل - $market')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: SingleChildScrollView(
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
                        'التوصية: $recommendation',
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text('الثقة: $confidence'),
                      Text('الدخول: $entry'),
                      Text('الوقف: $stop'),
                      Text('الأهداف: $targets'),
                      Text('RRR: $rrr'),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'أفضل 3 استراتيجيات:',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              if (strategies.isEmpty)
                const Text('لا توجد استراتيجيات لعرضها.',
                    style: TextStyle(color: Colors.white70))
              else
                ...strategies.map((strategy) {
                  final name = strategy['name'] ?? 'استراتيجية غير معروفة';
                  final description =
                      strategy['logic'] ?? strategy['description'] ?? '-';
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(8.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(name,
                              style:
                                  const TextStyle(fontWeight: FontWeight.bold)),
                          const SizedBox(height: 4),
                          Text(description),
                        ],
                      ),
                    ),
                  );
                }).toList(),
              const SizedBox(height: 16),
              ElevatedButton(
                  onPressed: exportToPDF, child: const Text('تصدير PDF')),
            ],
          ),
        ),
      ),
    );
  }
}
