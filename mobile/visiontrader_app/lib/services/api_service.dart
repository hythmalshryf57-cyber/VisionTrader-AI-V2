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

  Map<String, String> _authHeaders(String token, {bool jsonContent = true}) {
    final headers = <String, String>{
      'Authorization': 'Bearer $token',
    };
    if (jsonContent) {
      headers['Content-Type'] = 'application/json';
    }
    return headers;
  }

  Future<List<dynamic>> getAdminUsers(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/admin/users'),
      headers: _authHeaders(token, jsonContent: false),
    );
    return jsonDecode(response.body) as List<dynamic>;
  }

  Future<List<dynamic>> getAdminInviteCodes(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/admin/invite-codes'),
      headers: _authHeaders(token, jsonContent: false),
    );
    return jsonDecode(response.body) as List<dynamic>;
  }

  Future<Map<String, dynamic>> createInviteCode(
    String token,
    String code,
    int maxUses,
    String expiryDate,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/admin/invite-codes'),
      headers: _authHeaders(token),
      body: jsonEncode({
        'code': code,
        'max_uses': maxUses,
        'expiry_date': expiryDate,
      }),
    );
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> toggleInviteCode(
    String token,
    String code,
    bool active,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/admin/invite-codes/toggle'),
      headers: _authHeaders(token),
      body: jsonEncode({'code': code, 'active': active}),
    );
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> freezeUser(
    String token,
    String userId,
    bool freeze,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/admin/users/freeze'),
      headers: _authHeaders(token),
      body: jsonEncode({'user_id': userId, 'freeze': freeze}),
    );
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> killUserSession(
    String token,
    String userId,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/admin/users/kill-session'),
      headers: _authHeaders(token),
      body: jsonEncode({'user_id': userId}),
    );
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> getSystemHealth(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/admin/system-health'),
      headers: _authHeaders(token, jsonContent: false),
    );
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> askAI(
    String token,
    String question,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/ai/assistant'),
      headers: _authHeaders(token),
      body: jsonEncode({'question': question}),
    );
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<List<dynamic>> getStrategies(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/system/strategies'),
      headers: _authHeaders(token, jsonContent: false),
    );
    return jsonDecode(response.body) as List<dynamic>;
  }

  Future<Map<String, dynamic>> updateStrategyWeight(
    String token,
    String name,
    double weight,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/system/tune-weights'),
      headers: _authHeaders(token),
      body: jsonEncode({'strategy_name': name, 'weight': weight}),
    );
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> getStrategyComparison(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/system/strategy-comparison'),
      headers: _authHeaders(token, jsonContent: false),
    );
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> compareMarkets(
    String token,
    List<String> markets,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/markets/compare'),
      headers: _authHeaders(token),
      body: jsonEncode({'markets': markets}),
    );
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getSystemPulse(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/system/pulse'),
      headers: _authHeaders(token, jsonContent: false),
    );
    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}
