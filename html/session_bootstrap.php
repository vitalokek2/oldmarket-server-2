<?php
$lifetime = 60 * 60 * 24 * 7;

session_name('OLDMARKETSESSID');

if (PHP_VERSION_ID >= 70300) {
    session_set_cookie_params([
        'lifetime' => $lifetime,
        'path' => '/',
        'secure' => false,
        'httponly' => true,
        'samesite' => 'Lax'
    ]);
} else {
    session_set_cookie_params($lifetime, '/; samesite=Lax', '', false, true);
}

ini_set('session.gc_maxlifetime', (string)$lifetime);
ini_set('session.cookie_lifetime', (string)$lifetime);

session_start();

if (isset($_COOKIE[session_name()])) {
    setcookie(
        session_name(),
        session_id(),
        time() + $lifetime,
        '/',
        '',
        $isHttps,
        true
    );
}