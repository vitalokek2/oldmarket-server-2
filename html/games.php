<?php
require_once 'android_versions.php';
require_once __DIR__ . '/auth_cookie.php';
$auth = auth_user();

$real_ip = $_SERVER['HTTP_CLIENT_IP']
    ?? $_SERVER['HTTP_X_FORWARDED_FOR']
    ?? $_SERVER['REMOTE_ADDR'];

function load_api($url, $ip) {
    $opts = [
        "http" => [
            "header" => "X-Real-IP: $ip\r\n"
        ]
    ];
    return @file_get_contents($url, false, stream_context_create($opts));
}

$apps = json_decode(load_api('http://192.168.1.190:5000/api/apps', $real_ip), true);
$games = array_filter($apps, fn($app) => $app['is_game']);

$topGamesResponse = load_api('http://192.168.1.190:5000/api/top-games', $real_ip);
$topGames = $topGamesResponse ? json_decode($topGamesResponse, true) : [];

$bannerResponse = load_api('http://192.168.1.190:5000/api/banners', $real_ip);
$banners = $bannerResponse ? json_decode($bannerResponse, true) : [];
if (!is_array($banners)) $banners = [];
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <title>OldMarket - Игры</title>
  <link rel="stylesheet" href="style.css">
</head>
  <div class="sticky-header-section">
    <header class="topnav">
      <div class="logo">
        <img src="logo.png" alt="Android Market Logo" width="260">
        <p id="visitorCount" style="color: rgb(224, 224, 224); font-size: 0.8em;"></p>
      </div>
<div class="user-section">
  <?php if ($auth): ?>
      <a href="profile.php" style="color: white; text-decoration: none; display: flex; align-items: center; gap: 8px;">
          <img src="<?= API_BASE ?>/html/avatars/<?= htmlspecialchars($auth['avatar'] ?? 'default_avatar.png') ?>"
              width="25" height="25" style="border-radius: 50%;">
          <div>
              <div class="<?= ($auth['is_premium'] ?? 0) ? 'premium-user' : '' ?>">
                <?= htmlspecialchars($auth['username'] ?? '') ?>
              </div>
          </div>
      </a>
      <a href="logout.php" style="color: white; margin-left: 10px;">Выйти</a>
  <?php else: ?>
      <a href="login.php" style="color: white;">Войти</a>
      <a href="register.php" style="color: white; margin-left: 10px;">Регистрация</a>
  <?php endif; ?>
</div>
    </header>
    <div class="search-container">
      <input type="text" id="searchInput" placeholder="Поиск" onkeyup="searchApps()">
    </div>
  </div>
<body>
<div class="banner" id="banner"
     data-interval="5000"
     style="width:100%; text-align:center; overflow:hidden; cursor:pointer;">
  <?php if (!empty($banners)): ?>
    <a id="bannerLink" href="<?= htmlspecialchars($banners[0]['url'] ?? '') ?>" target="_blank" rel="noopener">
      <img id="bannerImg"
           src="http://192.168.1.190:5000/html/banners/<?= htmlspecialchars($banners[0]['image']) ?>"
           alt="Баннер"
           style="max-width:100%; width:100%; height:auto; border:0;">
    </a>
  <?php else: ?>
    <img id="bannerImg" src="banner1.jpg" alt="Баннер"
         style="max-width:100%; width:100%; height:auto; border:0;">
  <?php endif; ?>
</div>
    <script>
        function searchApps() {
          var query = document.getElementById('searchInput').value.toLowerCase();
          var apps = document.getElementsByClassName('app');
          
          for (var i = 0; i < apps.length; i++) {
              var appName = apps[i].getElementsByClassName('app-title')[0].textContent.toLowerCase();
              if (appName.indexOf(query) !== -1) {
                  apps[i].style.display = 'flex';
              } else {
                  apps[i].style.display = 'none';
              }
          }
      }

      var BANNERS = <?php echo json_encode($banners, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE); ?>;

      function onReady(fn) {
        if (document.readyState === 'complete' || document.readyState === 'interactive') {
          setTimeout(fn, 0);
        } else if (document.addEventListener) {
          document.addEventListener('DOMContentLoaded', fn, false);
        } else if (document.attachEvent) {
          document.attachEvent('onreadystatechange', function () {
            if (document.readyState === 'complete') { fn(); }
          });
        }
      }

      onReady(function () {
        if (!BANNERS || !BANNERS.length) return;

        var imgEl = document.getElementById('bannerImg');
        var linkEl = document.getElementById('bannerLink');
        if (!imgEl) return;

        var changeMs = 5000;
        var bannerWrap = document.getElementById('banner');
        if (bannerWrap) {
          var intervalAttr = bannerWrap.getAttribute('data-interval');
          var tmp = parseInt(intervalAttr, 10);
          if (!isNaN(tmp) && tmp > 0) changeMs = tmp;
        }

        for (var i = 0; i < BANNERS.length; i++) {
          if (BANNERS[i] && BANNERS[i].image) {
            var im = new Image();
            im.src = "http://192.168.1.190:5000/html/banners/" + BANNERS[i].image;
          }
        }

        var idx = 0;

        function applyBanner(i) {
          var b = BANNERS[i] || {};
          var src = "http://192.168.1.190:5000/html/banners/" + (b.image || "");
          imgEl.src = src;

          if (linkEl) {
            var url = (b.url || "").trim();
            if (url) {
              linkEl.href = url;
              linkEl.style.pointerEvents = "auto";
            } else {
              // если ссылка пустая — делаем некликабельным
              linkEl.href = "#";
              linkEl.style.pointerEvents = "none";
            }
          }
        }

        applyBanner(idx);

        setInterval(function () {
          if (BANNERS.length < 2) return;
          idx = (idx + 1) % BANNERS.length;
          applyBanner(idx);
        }, changeMs);
      });

      function installApp(appId) {
          window.location.href = 'app.php?id=' + appId;
      }
    </script>

  <main>
    <section class="featured">
      <h2 style="color: white; text-align: center;">Популярные игры</h2>
      <div class="app-list">
        <?php foreach ($topGames as $game): ?>
        <div class="app" onclick="installApp(<?= $game['id'] ?>)">
          <img src="http://192.168.1.190:5000/html/apps/<?= $game['icon'] ?>" width="55">
          <div class="app-info">
            <span class="app-title"><?= htmlspecialchars($game['name']) ?></span><br>
            <span>Рейтинг: <?= $game['rating'] ?> ★</span><br>
            <span>Скачиваний: <?= $game['downloads'] ?></span><br>
            <span>Android <?= apiToAndroidVersion($game['api']) ?></span>
          </div>
        </div>
        <?php endforeach; ?>
      </div>
      
      <h2 style="color: white; text-align: center; margin-top: 30px;">Все игры</h2>
      <div class="app-list">
        <div class="add">
          <img src="apps.jpg" alt="Приложения" width="190" class="button-image" onclick="window.location.href='index.php'">
        </div>
        <?php foreach ($games as $game): ?>
        <div class="app" onclick="installApp(<?= $game['id'] ?>)">
          <img src="http://192.168.1.190:5000/html/apps/<?= $game['icon'] ?>" width="55">
          <div class="app-info">
            <span class="app-title"><?= htmlspecialchars($game['name']) ?></span><br>
            <span>Рейтинг: <?= $game['rating'] ?> ★</span><br>
            <span>Скачиваний: <?= $game['downloads'] ?></span><br>
            <span>Android <?= apiToAndroidVersion($game['api']) ?></span>
          </div>
        </div>
        <?php endforeach; ?>
      </div>
    </section>
  </main>
  <div class="footer">
    <p>OldMarket &copy; 2025-2026</p>
  </div>
</body>
</html>