import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String localBaseUrl = 'http://127.0.0.1:8000';
  static const String prodBaseUrl = 'https://your-render-url.onrender.com';
  static String baseUrl = const String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: localBaseUrl,
  );

  static void setProduction(bool useProduction) {
    baseUrl = useProduction ? prodBaseUrl : localBaseUrl;
  }

  static void setBaseUrl(String url) {
    baseUrl = url;
  }

  Future<Map<String, dynamic>> login(
    String email,
    String password,
    String inviteCode,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
        'invite_code': inviteCode,
      }),
    );
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> register(
    String email,
    String password,
    String inviteCode,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
        'invite_code': inviteCode,
      }),
    );
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> uploadAnalysis(
    String token,
    Map<String, dynamic> data,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/analysis/upload'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode(data),
    );
    return jsonDecode(response.body);
  }

  Future<List<dynamic>> getHistory(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/history'),
      headers: {'Authorization': 'Bearer $token'},
    );
    return jsonDecode(response.body);
  }

  Future<List<dynamic>> getCalendar(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/calendar'),
      headers: {'Authorization': 'Bearer $token'},
    );
    return jsonDecode(response.body);
  }

  Future<List<dynamic>> getAlerts(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/alerts'),
      headers: {'Authorization': 'Bearer $token'},
    );
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> calculateRisk(
    String token,
    Map<String, dynamic> data,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/risk/calculate'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode(data),
    );
    return jsonDecode(response.body);
  }
}
