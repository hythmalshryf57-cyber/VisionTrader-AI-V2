import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'services/notification_service.dart';
import 'screens/login_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/admin_screen.dart';
import 'screens/ask_ai_screen.dart';
import 'screens/strategy_factory_screen.dart';
import 'screens/heatmap_screen.dart';
import 'screens/academy_screen.dart';
import 'screens/service_health_screen.dart';
import 'screens/strategy_battle_screen.dart';
import 'upload_screen.dart';
import 'result_screen.dart';
import 'history_screen.dart';
import 'calendar_screen.dart';
import 'settings_screen.dart';
import 'backtest_screen.dart';
import 'journal_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  await NotificationService.initialize();
  runApp(const VisionTraderApp());
}

class VisionTraderApp extends StatelessWidget {
  const VisionTraderApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'VisionTrader AI',
      theme: ThemeData(
        brightness: Brightness.dark,
        primaryColor: const Color(0xFF5B67CA),
        scaffoldBackgroundColor: const Color(0xFF181A20),
        colorScheme: ColorScheme.dark(
          primary: Color(0xFF5B67CA),
          secondary: Color(0xFF23243A),
        ),
        fontFamily: 'Cairo',
      ),
      initialRoute: '/',
      routes: {
        '/': (context) => const LoginScreen(),
        '/dashboard': (context) => const DashboardScreen(),
        '/upload': (context) => UploadScreen(),
        '/result': (context) => ResultScreen(
            result: ModalRoute.of(context)!.settings.arguments
                as Map<String, dynamic>),
        '/history': (context) => HistoryScreen(),
        '/calendar': (context) => CalendarScreen(),
        '/settings': (context) => SettingsScreen(),
        '/backtest': (context) => BacktestScreen(),
        '/journal': (context) => JournalScreen(),
        '/admin': (context) => const AdminScreen(),
        '/ask_ai': (context) => const AskAiScreen(),
        '/strategy_factory': (context) => const StrategyFactoryScreen(),
        '/heatmap': (context) => const HeatmapScreen(),
        '/academy': (context) => const AcademyScreen(),
        '/service_health': (context) => const ServiceHealthScreen(),
        '/strategy_battle': (context) => const StrategyBattleScreen(),
      },
    );
  }
}
