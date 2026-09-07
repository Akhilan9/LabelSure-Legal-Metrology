import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

class ApiException implements Exception {
  final int statusCode;
  final String message;
  final dynamic details;

  ApiException({
    required this.statusCode,
    required this.message,
    this.details,
  });

  @override
  String toString() => message;
}

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  ApiClient._internal();

  String baseUrl = 'http://127.0.0.1:8000/api/v1';
  String? _accessToken;
  void Function()? onUnauthorized;

  void setAccessToken(String? token) {
    _accessToken = token;
  }

  String? get accessToken => _accessToken;

  Map<String, String> _headers([Map<String, String>? extra]) {
    final headers = <String, String>{
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
    if (_accessToken != null) {
      headers['Authorization'] = 'Bearer $_accessToken';
    }
    if (extra != null) {
      headers.addAll(extra);
    }
    return headers;
  }

  Uri _buildUri(String path, [Map<String, dynamic>? queryParams]) {
    String cleanPath = path;
    if (cleanPath.startsWith('http://') || cleanPath.startsWith('https://')) {
      final parsed = Uri.parse(cleanPath);
      cleanPath = parsed.path;
      if (cleanPath.startsWith('/api/v1/')) {
        cleanPath = cleanPath.substring(7);
      } else if (cleanPath.startsWith('/api/v1')) {
        cleanPath = cleanPath.substring(7);
      }
    }
    if (cleanPath.startsWith('/api/v1/')) {
      cleanPath = cleanPath.substring(7);
    } else if (cleanPath.startsWith('/api/v1')) {
      cleanPath = cleanPath.substring(7);
    }
    if (!cleanPath.startsWith('/')) {
      cleanPath = '/$cleanPath';
    }

    final fullUrl = '$baseUrl$cleanPath';
    final uri = Uri.parse(fullUrl);
    if (queryParams != null && queryParams.isNotEmpty) {
      final stringParams = queryParams.map((k, v) => MapEntry(k, v.toString()));
      return uri.replace(queryParameters: {...uri.queryParameters, ...stringParams});
    }
    return uri;
  }

  dynamic _handleResponse(http.Response response) {
    if (response.statusCode == 401) {
      onUnauthorized?.call();
      throw ApiException(
        statusCode: 401,
        message: 'Your session has expired. Please sign in again.',
      );
    }

    dynamic body;
    if (response.body.isNotEmpty) {
      try {
        body = jsonDecode(utf8.decode(response.bodyBytes));
      } catch (_) {
        body = response.body;
      }
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return body;
    }

    String errorMsg = 'Request failed with status ${response.statusCode}';
    if (body is Map && body.containsKey('detail')) {
      final detail = body['detail'];
      if (detail is String) {
        errorMsg = detail;
      } else if (detail is List) {
        errorMsg = detail.map((d) => d['msg'] ?? d.toString()).join('; ');
      }
    }

    throw ApiException(
      statusCode: response.statusCode,
      message: errorMsg,
      details: body,
    );
  }

  Future<dynamic> get(String path, {Map<String, dynamic>? queryParams}) async {
    final uri = _buildUri(path, queryParams);
    final response = await http
        .get(uri, headers: _headers())
        .timeout(const Duration(seconds: 45));
    return _handleResponse(response);
  }

  Future<Uint8List> getBytes(String path, {Map<String, dynamic>? queryParams}) async {
    final uri = _buildUri(path, queryParams);
    final headers = <String, String>{};
    if (_accessToken != null) {
      headers['Authorization'] = 'Bearer $_accessToken';
    }
    final response = await http
        .get(uri, headers: headers)
        .timeout(const Duration(seconds: 60));

    if (response.statusCode == 401) {
      onUnauthorized?.call();
      throw ApiException(
        statusCode: 401,
        message: 'Your session has expired.',
      );
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return response.bodyBytes;
    }

    throw ApiException(
      statusCode: response.statusCode,
      message: 'Failed to download data.',
    );
  }

  Future<dynamic> post(
    String path, {
    dynamic body,
    Map<String, dynamic>? queryParams,
    Duration timeout = const Duration(seconds: 120),
  }) async {
    final uri = _buildUri(path, queryParams);
    final response = await http
        .post(
          uri,
          headers: _headers(),
          body: body != null ? jsonEncode(body) : null,
        )
        .timeout(timeout);
    return _handleResponse(response);
  }

  Future<dynamic> patch(
    String path, {
    dynamic body,
    Map<String, dynamic>? queryParams,
  }) async {
    final uri = _buildUri(path, queryParams);
    final response = await http
        .patch(
          uri,
          headers: _headers(),
          body: body != null ? jsonEncode(body) : null,
        )
        .timeout(const Duration(seconds: 45));
    return _handleResponse(response);
  }

  Future<dynamic> delete(String path, {Map<String, dynamic>? queryParams}) async {
    final uri = _buildUri(path, queryParams);
    final response = await http
        .delete(uri, headers: _headers())
        .timeout(const Duration(seconds: 45));
    return _handleResponse(response);
  }

  /// Upload multiple files with panel types matching FastAPI endpoint
  Future<dynamic> uploadFiles(
    String path, {
    required List<({String filename, Uint8List bytes, String panelType})> files,
  }) async {
    final uri = _buildUri(path);
    final request = http.MultipartRequest('POST', uri);

    if (_accessToken != null) {
      request.headers['Authorization'] = 'Bearer $_accessToken';
    }

    for (final item in files) {
      request.files.add(http.MultipartFile.fromBytes(
        'files',
        item.bytes,
        filename: item.filename,
      ));
      request.fields['panel_types'] = item.panelType;
    }

    final streamedResponse = await request.send().timeout(const Duration(minutes: 3));
    final response = await http.Response.fromStream(streamedResponse);
    return _handleResponse(response);
  }

  Future<Uint8List> postBytes(
    String path, {
    dynamic body,
    Duration timeout = const Duration(seconds: 60),
  }) async {
    final uri = _buildUri(path);
    final response = await http
        .post(
          uri,
          headers: _headers(),
          body: body != null ? jsonEncode(body) : null,
        )
        .timeout(timeout);

    if (response.statusCode == 401) {
      onUnauthorized?.call();
      throw ApiException(
        statusCode: 401,
        message: 'Your session has expired.',
      );
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return response.bodyBytes;
    }

    throw ApiException(
      statusCode: response.statusCode,
      message: 'Failed to download data.',
    );
  }

  Future<dynamic> uploadCenterItem({
    required String centerName,
    required String category,
    required String location,
    String? productName,
    String? brandName,
    String panelType = 'FRONT',
    required List<({String filename, Uint8List bytes})> files,
  }) async {
    final uri = _buildUri('/inspection-center/analyze-item');
    final request = http.MultipartRequest('POST', uri);

    if (_accessToken != null) {
      request.headers['Authorization'] = 'Bearer $_accessToken';
    }

    request.fields['center_name'] = centerName;
    request.fields['category'] = category;
    request.fields['location'] = location;
    if (productName != null && productName.isNotEmpty) {
      request.fields['product_name'] = productName;
    }
    if (brandName != null && brandName.isNotEmpty) {
      request.fields['brand_name'] = brandName;
    }
    request.fields['panel_type'] = panelType;

    for (final item in files) {
      request.files.add(http.MultipartFile.fromBytes(
        'files',
        item.bytes,
        filename: item.filename,
      ));
    }

    final streamedResponse = await request.send().timeout(const Duration(minutes: 5));
    final response = await http.Response.fromStream(streamedResponse);
    return _handleResponse(response);
  }
}
