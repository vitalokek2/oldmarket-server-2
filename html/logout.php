<?php
require_once __DIR__ . '/auth_cookie.php';
auth_clear_cookies();
header("Location: /index.php");
exit;