<?php
require_once __DIR__ . '/auth_cookie.php';

header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');

$error = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? '');
    $password = trim($_POST['password'] ?? '');

    $res = api_post_json('/api/login', [
        'username' => $username,
        'password' => $password
    ]);

    if ($res === false) {
        $error = "Ошибка соединения с сервером";
    } else {
        $j = json_decode($res, true);

        if (is_array($j) && !empty($j['success'])) {
            $uid = (int)$j['user_id'];
            $uname = (string)$j['username'];

            $avatar = 'default_avatar.png';
            $is_premium = 0;

            $profile_json = api_get('/api/user/' . $uid . '/profile');
            if ($profile_json !== false) {
                $p = json_decode($profile_json, true);
                if (is_array($p) && empty($p['error'])) {
                    $avatar = $p['avatar'] ?? $avatar;
                    $is_premium = (int)($p['is_premium'] ?? 0);
                }
            }

            auth_set_cookies($uid, $uname, $avatar, $is_premium);
            header("Location: /index.php");
            exit;
        } else {
            $error = $j['error'] ?? "Неверный логин или пароль";
        }
    }
}
?>
<!DOCTYPE html>
<html>
<head>
    <title>Вход - OldMarket</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background-image: url(background.jpg); background-repeat: repeat; background-size: 5%; color: white; font-family: Arial; }
        .login-form { max-width: 300px; margin: 100px auto; padding: 20px; background: #4444445e; }
        input { width: 100%; padding: 10px; margin: 5px 0; }
        button { width: 100%; padding: 10px; background: #a0b532; color: white; border: none; }
    </style>
</head>
<body>
    <div class="login-form">
        <h2>Вход</h2>
        <?php if ($error): ?>
            <p style="color: red;"><?= htmlspecialchars($error) ?></p>
        <?php endif; ?>
        <form method="POST">
            <input type="text" name="username" placeholder="Имя пользователя" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Войти</button>
        </form>
        <p>Нет аккаунта? <a href="register.php" style="color: #a0b532;">Зарегистрироваться</a></p>
    </div>
</body>
</html>