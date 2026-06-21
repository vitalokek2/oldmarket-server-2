<?php
define('AUTH_SECRET', '');

function auth_set($user_id, $username, $avatar = 'default_avatar.png', $is_premium = 0) {
    $payload = [
        'user_id' => (int)$user_id,
        'username' => (string)$username,
        'avatar' => (string)$avatar,
        'is_premium' => (int)$is_premium,
        'ts' => time()
    ];
    $json = json_encode($payload, JSON_UNESCAPED_UNICODE);
    $sig = hash_hmac('sha256', $json, AUTH_SECRET);
    $value = base64_encode($json) . '.' . $sig;

    setcookie('OLDMARKET_AUTH', $value, time() + 60*60*24*7, '/', '', false, true);
}

function auth_clear() {
    setcookie('OLDMARKET_AUTH', '', time() - 3600, '/', '', false, true);
}

function auth_get() {
    if (empty($_COOKIE['OLDMARKET_AUTH'])) return null;
    $parts = explode('.', $_COOKIE['OLDMARKET_AUTH'], 2);
    if (count($parts) !== 2) return null;

    $json = base64_decode($parts[0], true);
    if ($json === false) return null;

    $sig = $parts[1];
    $calc = hash_hmac('sha256', $json, AUTH_SECRET);
    if (!hash_equals($calc, $sig)) return null;

    $data = json_decode($json, true);
    if (!is_array($data) || empty($data['user_id'])) return null;

    if (!empty($data['ts']) && time() - (int)$data['ts'] > 60*60*24*7) {
        return null;
    }
    return $data;
}