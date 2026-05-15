import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'widgets/common_widgets.dart';

class UploadScreen extends StatefulWidget {
  @override
  _UploadScreenState createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  String? selectedMarket;
  String? selectedTimeframe;
  List<File> selectedImages = [];
  bool isLoading = false;

  final List<String> markets = ['ذهب', 'عملات', 'مؤشرات', 'نفط'];
  final List<String> timeframes = ['سكالبينج', 'يومي', 'سوينغ', 'استثماري'];

  final ImagePicker _picker = ImagePicker();

  Future<void> pickImage(ImageSource source) async {
    final XFile? image = await _picker.pickImage(source: source);
    if (image != null) {
      setState(() {
        selectedImages.add(File(image.path));
      });
    }
  }

  Future<void> startAnalysis() async {
    if (selectedMarket == null ||
        selectedTimeframe == null ||
        selectedImages.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('يرجى اختيار السوق، الإطار الزمني، ورفع صور')),
      );
      return;
    }

    setState(() {
      isLoading = true;
    });

    // Simulate API call
    // Replace with actual API endpoint
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('https://your-api-endpoint.com/analyze'),
    );
    request.fields['market'] = selectedMarket!;
    request.fields['timeframe'] = selectedTimeframe!;

    for (var image in selectedImages) {
      request.files.add(
        await http.MultipartFile.fromPath('images', image.path),
      );
    }

    try {
      var response = await request.send();
      if (response.statusCode == 200) {
        var responseData = await response.stream.bytesToString();
        var result = json.decode(responseData);
        // Navigate to result screen with result
        Navigator.pushNamed(context, '/result', arguments: result);
      } else {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('فشل في التحليل')));
      }
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('خطأ في الاتصال')));
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('رفع الصور للتحليل')),
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
              hint: Text('اختر حزمة الأطر الزمنية'),
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
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                ElevatedButton(
                  onPressed: () => pickImage(ImageSource.gallery),
                  child: Text('معرض'),
                ),
                ElevatedButton(
                  onPressed: () => pickImage(ImageSource.camera),
                  child: Text('كاميرا'),
                ),
                ElevatedButton(
                  onPressed: selectedImages.length < 3
                      ? () => pickImage(ImageSource.gallery)
                      : null,
                  child: Text('صورة إضافية'),
                ),
              ],
            ),
            SizedBox(height: 16),
            Expanded(
              child: GridView.builder(
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 3,
                  crossAxisSpacing: 4.0,
                  mainAxisSpacing: 4.0,
                ),
                itemCount: selectedImages.length,
                itemBuilder: (context, index) {
                  return Image.file(selectedImages[index], fit: BoxFit.cover);
                },
              ),
            ),
            SizedBox(height: 16),
            isLoading
                ? const Column(
                    children: [
                      CircularProgressIndicator(),
                      SizedBox(height: 16),
                      SkeletonLoader(width: 200, height: 20),
                      SizedBox(height: 8),
                      SkeletonLoader(width: 150, height: 16),
                    ],
                  )
                : PulsingButton(
                    onPressed: startAnalysis,
                    child: const Text(
                      'ابدأ التحليل',
                      style: TextStyle(
                          color: Colors.white, fontWeight: FontWeight.bold),
                    ),
                  ),
          ],
        ),
      ),
    );
  }
}
