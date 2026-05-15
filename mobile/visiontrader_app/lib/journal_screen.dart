import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class JournalScreen extends StatefulWidget {
  @override
  _JournalScreenState createState() => _JournalScreenState();
}

class _JournalScreenState extends State<JournalScreen> {
  final TextEditingController beforeFeelingController = TextEditingController();
  final TextEditingController afterFeelingController = TextEditingController();
  String? selectedEmotion;
  List<Map<String, dynamic>> journalEntries = [];

  final List<String> emotions = ['سعيد', 'حزين', 'غاضب', 'مرتاح', 'قلق'];

  @override
  void initState() {
    super.initState();
    loadJournal();
  }

  Future<void> loadJournal() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    String? journalData = prefs.getString('journal');
    if (journalData != null) {
      setState(() {
        journalEntries = List<Map<String, dynamic>>.from(
          json.decode(journalData),
        );
      });
    }
  }

  Future<void> saveEntry() async {
    if (beforeFeelingController.text.isEmpty ||
        afterFeelingController.text.isEmpty ||
        selectedEmotion == null) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('يرجى ملء جميع الحقول')));
      return;
    }

    Map<String, dynamic> entry = {
      'date': DateTime.now().toIso8601String(),
      'beforeFeeling': beforeFeelingController.text,
      'afterFeeling': afterFeelingController.text,
      'emotion': selectedEmotion,
    };

    setState(() {
      journalEntries.add(entry);
    });

    SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.setString('journal', json.encode(journalEntries));

    beforeFeelingController.clear();
    afterFeelingController.clear();
    setState(() {
      selectedEmotion = null;
    });

    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('تم حفظ الإدخال')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('اليوميات')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(
              controller: beforeFeelingController,
              decoration: InputDecoration(labelText: 'الشعور قبل الصفقة'),
            ),
            SizedBox(height: 16),
            TextField(
              controller: afterFeelingController,
              decoration: InputDecoration(labelText: 'الشعور بعد الصفقة'),
            ),
            SizedBox(height: 16),
            DropdownButton<String>(
              hint: Text('اختر المشاعر'),
              value: selectedEmotion,
              onChanged: (String? newValue) {
                setState(() {
                  selectedEmotion = newValue;
                });
              },
              items: emotions.map<DropdownMenuItem<String>>((String value) {
                return DropdownMenuItem<String>(
                  value: value,
                  child: Text(value),
                );
              }).toList(),
            ),
            SizedBox(height: 16),
            ElevatedButton(onPressed: saveEntry, child: Text('حفظ الإدخال')),
            SizedBox(height: 16),
            Expanded(
              child: ListView.builder(
                itemCount: journalEntries.length,
                itemBuilder: (context, index) {
                  var entry = journalEntries[index];
                  return Card(
                    child: ListTile(
                      title: Text('التاريخ: ${entry['date'].split('T')[0]}'),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('قبل: ${entry['beforeFeeling']}'),
                          Text('بعد: ${entry['afterFeeling']}'),
                          Text('المشاعر: ${entry['emotion']}'),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
