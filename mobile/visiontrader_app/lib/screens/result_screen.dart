import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdf/widgets.dart' as pw;
import '../widgets/common_widgets.dart';

class ResultScreen extends StatelessWidget {
  final Map<String, dynamic> analysisResult;

  const ResultScreen({Key? key, required this.analysisResult})
      : super(key: key);

  Future<void> _exportPdf(BuildContext context) async {
    final doc = pw.Document();
    final recommendation = analysisResult['recommendation'] ?? 'N/A';
    final confidence = analysisResult['confidence'] ?? 'N/A';
    final entry = analysisResult['entry'] ?? 'N/A';
    final stop = analysisResult['stop'] ?? 'N/A';
    final targets = analysisResult['targets']?.join(', ') ?? 'N/A';
    final rrr = analysisResult['rrr'] ?? 'N/A';
    final strategies = List<Map<String, dynamic>>.from(
      analysisResult['strategies'] ?? [],
    );

    doc.addPage(
      pw.Page(
        build: (context) {
          return pw.Column(
            crossAxisAlignment: pw.CrossAxisAlignment.start,
            children: [
              pw.Text(
                'تقرير تحليل VisionTrader',
                style: pw.TextStyle(
                  fontSize: 24,
                  fontWeight: pw.FontWeight.bold,
                ),
              ),
              pw.SizedBox(height: 18),
              pw.Text(
                'توصية: $recommendation',
                style: pw.TextStyle(fontSize: 18),
              ),
              pw.Text('ثقة: $confidence', style: pw.TextStyle(fontSize: 18)),
              pw.Text('دخول: $entry', style: pw.TextStyle(fontSize: 18)),
              pw.Text('وقف: $stop', style: pw.TextStyle(fontSize: 18)),
              pw.Text('أهداف: $targets', style: pw.TextStyle(fontSize: 18)),
              pw.Text('RRR: $rrr', style: pw.TextStyle(fontSize: 18)),
              pw.SizedBox(height: 22),
              pw.Text(
                'أفضل 3 استراتيجيات',
                style: pw.TextStyle(
                  fontSize: 20,
                  fontWeight: pw.FontWeight.bold,
                ),
              ),
              pw.SizedBox(height: 12),
              ...strategies.take(3).map((strategy) {
                return pw.Column(
                  crossAxisAlignment: pw.CrossAxisAlignment.start,
                  children: [
                    pw.Text(
                      '- ${strategy['name'] ?? 'استراتيجية'}',
                      style: pw.TextStyle(
                        fontSize: 16,
                        fontWeight: pw.FontWeight.bold,
                      ),
                    ),
                    pw.Text(
                      '${strategy['logic'] ?? 'منطق غير متوفر'}',
                      style: pw.TextStyle(fontSize: 14),
                    ),
                    pw.SizedBox(height: 10),
                  ],
                );
              }),
            ],
          );
        },
      ),
    );

    final directory = await getTemporaryDirectory();
    final file = File('${directory.path}/visiontrader_analysis.pdf');
    await file.writeAsBytes(await doc.save());

    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('تم حفظ التقرير في: ${file.path}')),
      );
    }
  }

  Widget _buildInfoTile(String label, String value) {
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 0, vertical: 4),
      title: Text(label, style: const TextStyle(color: Colors.white70)),
      trailing: Text(
        value,
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Widget _buildStrategyCard(Map<String, dynamic> strategy) {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            strategy['name'] ?? 'استراتيجية',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.bold,
              fontFamily: 'monospace',
            ),
          ),
          const SizedBox(height: 8),
          Text(
            strategy['logic'] ?? 'منطق الاستراتيجية غير متوفر',
            style: const TextStyle(color: Colors.white70),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final recommendation =
        analysisResult['recommendation']?.toString() ?? 'N/A';
    final confidence = analysisResult['confidence']?.toString() ?? 'N/A';
    final entry = analysisResult['entry']?.toString() ?? 'N/A';
    final stop = analysisResult['stop']?.toString() ?? 'N/A';
    final targets =
        (analysisResult['targets'] as List<dynamic>?)?.join(' - ') ?? 'N/A';
    final rrr = analysisResult['rrr']?.toString() ?? 'N/A';
    final strategies = List<Map<String, dynamic>>.from(
      analysisResult['strategies'] ?? [],
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('نتيجة التحليل'),
        backgroundColor: const Color(0xFF23243A),
      ),
      backgroundColor: const Color(0xFF181A20),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              GlassCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text(
                      'إشارة التداول',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        fontFamily: 'monospace', // Tech font
                      ),
                    ),
                    const SizedBox(height: 16),
                    GoldenGlow(
                      isGlowing: int.tryParse(confidence) ?? 0 >= 90,
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.05),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          recommendation,
                          style: TextStyle(
                            color: recommendation == 'شراء'
                                ? Colors.green
                                : Colors.red,
                            fontSize: 28,
                            fontWeight: FontWeight.bold,
                            fontFamily: 'monospace',
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    GoldenGlow(
                      isGlowing: int.tryParse(confidence) ?? 0 >= 90,
                      child: _buildInfoTile('الثقة', '$confidence%'),
                    ),
                    _buildInfoTile('دخول', entry),
                    _buildInfoTile('وقف', stop),
                    _buildInfoTile('أهداف', targets),
                    _buildInfoTile('RRR', rrr),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              const Text(
                'أفضل 3 استراتيجيات',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 14),
              ...strategies.take(3).map(_buildStrategyCard),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () => _exportPdf(context),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF5B67CA),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: const Text('تصدير PDF', style: TextStyle(fontSize: 16)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
