<?php
require_once __DIR__ . '/config.php';

function auth_user() {
    $uid = isset($_COOKIE['OM_UID']) ? (int)$_COOKIE['OM_UID'] : 0;
    if ($uid <= 0) return null;

    return [
        'user_id' => $uid,
        'username' => isset($_COOKIE['OM_UNAME']) ? rawurldecode($_COOKIE['OM_UNAME']) : '',
        'avatar' => isset($_COOKIE['OM_AVATAR']) ? rawurldecode($_COOKIE['OM_AVATAR']) : 'default_avatar.png',
        'is_premium' => isset($_COOKIE['OM_PREMIUM']) ? (int)$_COOKIE['OM_PREMIUM'] : 0,
    ];
}

function auth_set_cookies($user_id, $username, $avatar, $is_premium) {
    $exp = time() + 60*60*24*7;
    setcookie('OM_UID', (string)((int)$user_id), $exp, '/', '', false, true);
    setcookie('OM_UNAME', rawurlencode((string)$username), $exp, '/', '', false, true);
    setcookie('OM_AVATAR', rawurlencode((string)$avatar), $exp, '/', '', false, true);
    setcookie('OM_PREMIUM', (string)((int)$is_premium), $exp, '/', '', false, true);
}

function auth_clear_cookies() {
    setcookie('OM_UID', '', time()-3600, '/', '', false, true);
    setcookie('OM_UNAME', '', time()-3600, '/', '', false, true);
    setcookie('OM_AVATAR', '', time()-3600, '/', '', false, true);
    setcookie('OM_PREMIUM', '', time()-3600, '/', '', false, true);
}

function real_ip() {
    $ip = $_SERVER['HTTP_CLIENT_IP']
        ?? $_SERVER['HTTP_X_FORWARDED_FOR']
        ?? $_SERVER['REMOTE_ADDR']
        ?? '';

    if (strpos($ip, ',') !== false) {
        $ip = trim(explode(',', $ip)[0]);
    }
    return trim($ip);
}

function api_get($path) {
    $ip = real_ip();
    $opts = [
        'http' => [
            'header' => "X-Real-IP: $ip\r\n",
            'timeout' => 15
        ]
    ];
    return @file_get_contents(API_BASE . $path, false, stream_context_create($opts));
}

function api_post_json($path, $payload) {
    $ip = real_ip();
    $opts = [
        'http' => [
            'method' => 'POST',
            'header' => "Content-Type: application/json\r\nX-Real-IP: $ip\r\n",
            'content' => json_encode($payload, JSON_UNESCAPED_UNICODE),
            'ignore_errors' => true,
            'timeout' => 15
        ]
    ];
    return @file_get_contents(API_BASE . $path, false, stream_context_create($opts));
}