<?php
require_once __DIR__ . '/auth_cookie.php';
require_once __DIR__ . '/site_ui.php';
require_once 'android_versions.php';

header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');

$auth = auth_user();

$apiResponse = api_get('/api/apps');
$allApps = $apiResponse ? json_decode($apiResponse, true) : [];
if (!is_array($allApps)) $allApps = [];

$mode = isset($_GET['mode']) ? trim($_GET['mode']) : 'apps';
if ($mode !== 'games') $mode = 'apps';

$items = [];
foreach ($allApps as $app) {
    $is_game = false;
    if (isset($app['is_game'])) {
        $is_game = filter_var($app['is_game'], FILTER_VALIDATE_BOOLEAN);
    }

    if ($mode === 'games') {
        if ($is_game === true) $items[] = $app;
    } else {
        if ($is_game === false) $items[] = $app;
    }
}

$topResponse = api_get($mode === 'games' ? '/api/top-games' : '/api/top-apps');
$topItems = $topResponse ? json_decode($topResponse, true) : [];
if (!is_array($topItems)) $topItems = [];

$bannerResponse = api_get('/api/banners');
$banners = $bannerResponse ? json_decode($bannerResponse, true) : [];
if (!is_array($banners)) $banners = [];

$perPage = 12;
$totalItems = count($items);
$totalPages = (int) ceil($totalItems / $perPage);
if ($totalPages < 1) $totalPages = 1;

$page = isset($_GET['page']) ? (int) $_GET['page'] : 1;
if ($page < 1) $page = 1;
if ($page > $totalPages) $page = $totalPages;

$offset = ($page - 1) * $perPage;
$pagedItems = array_slice($items, $offset, $perPage);

$topTitle = ($mode === 'games') ? om_t('Популярные игры', 'Popular games') : om_t('Популярные приложения', 'Popular apps');
$allTitle = ($mode === 'games') ? om_t('Все игры', 'All games') : om_t('Все приложения', 'All apps');
$toggleImage = ($mode === 'games') ? 'apps.jpg' : 'games.png';
$toggleAlt = ($mode === 'games') ? om_t('Приложения', 'Apps') : om_t('Игры', 'Games');
$toggleMode = ($mode === 'games') ? 'apps' : 'games';
$toggleWidth = ($mode === 'games') ? 190 : 190;
?>
<!DOCTYPE html>
<html lang="<?= htmlspecialchars(om_lang()) ?>">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <title>OldMarket</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
<?php render_site_header($auth, "index.php"); ?>
<div class="banner" id="banner"
     data-interval="5000"
     style="width:100%; text-align:center; overflow:hidden; cursor:pointer;">
  <?php if (!empty($banners)): ?>
    <a id="bannerLink" href="<?= htmlspecialchars(isset($banners[0]['url']) ? $banners[0]['url'] : '') ?>" target="_blank" rel="noopener">
      <img id="bannerImg"
           src="http://94.156.115.120:5000/html/banners/<?= htmlspecialchars($banners[0]['image']) ?>"
           alt="Баннер"
           style="max-width:100%; width:100%; height:auto; border:0;">
    </a>
  <?php else: ?>
    <img id="bannerImg" src="banner1.jpg" alt="Баннер"
         style="max-width:100%; width:100%; height:auto; border:0;">
  <?php endif; ?>
</div>
    <script>
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
            im.src = 'http://94.156.115.120:5000/html/banners/' + BANNERS[i].image;
          }
        }

        var idx = 0;

        function applyBanner(i) {
          var b = BANNERS[i] || {};
          var src = 'http://94.156.115.120:5000/html/banners/' + (b.image || '');
          imgEl.src = src;

          if (linkEl) {
            var url = (b.url || '').replace(/^\s+|\s+$/g, '');
            if (url) {
              linkEl.href = url;
              linkEl.style.pointerEvents = 'auto';
            } else {
              linkEl.href = '#';
              linkEl.style.pointerEvents = 'none';
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

      function switchMode(newMode) {
        window.location.href = 'index.php?mode=' + encodeURIComponent(newMode);
      }
    </script>

  <main>
    <section class="featured">
      <h2 style="color: white; text-align: center;"><?= htmlspecialchars($topTitle) ?></h2>
      <div class="app-list">
        <?php foreach ($topItems as $app): ?>
        <div class="app" onclick="installApp(<?= $app['id'] ?>)">
          <img src="http://94.156.115.120:5000/html/apps/<?= $app['icon'] ?>" width="55">
          <div class="app-info">
            <span class="app-title"><?= htmlspecialchars($app['name']) ?></span><br>
            <span><?= htmlspecialchars(om_t("Рейтинг", "Rating")) ?>: <?= $app['rating'] ?> ★</span><br>
            <span><?= htmlspecialchars(om_t("Скачиваний", "Downloads")) ?>: <?= $app['downloads'] ?></span><br>
            <span>Android <?= apiToAndroidVersion($app['api']) ?></span>
          </div>
        </div>
        <?php endforeach; ?>
      </div>

      <h2 style="color: white; text-align: center; margin-top: 30px;"><?= htmlspecialchars($allTitle) ?></h2>
      <div class="app-list">
        <?php if ($page == 1): ?>
        <div class="add">
          <img src="<?= htmlspecialchars($toggleImage) ?>" alt="<?= htmlspecialchars($toggleAlt) ?>" width="<?= $toggleWidth ?>" class="button-image" onclick="switchMode('<?= htmlspecialchars($toggleMode) ?>')">
        </div>
        <?php if ($mode === 'apps'): ?>
        <div class="add">
          <img src="category.jpg" alt="<?= htmlspecialchars(om_t("Категории", "Categories")) ?>" width="190" class="button-image" onclick="window.location.href='categories.php'">
        </div>
        <?php endif; ?>
        <?php endif; ?>

        <?php foreach ($pagedItems as $app): ?>
        <div class="app" onclick="installApp(<?= $app['id'] ?>)">
          <img src="http://94.156.115.120:5000/html/apps/<?= $app['icon'] ?>" width="55">
          <div class="app-info">
            <span class="app-title"><?= htmlspecialchars($app['name']) ?></span><br>
            <span><?= htmlspecialchars(om_t("Рейтинг", "Rating")) ?>: <?= $app['rating'] ?> ★</span><br>
            <span><?= htmlspecialchars(om_t("Скачиваний", "Downloads")) ?>: <?= $app['downloads'] ?></span><br>
            <span>Android <?= apiToAndroidVersion($app['api']) ?></span>
          </div>
        </div>
        <?php endforeach; ?>
      </div>

      <div id="pagination" style="text-align:center; margin: 25px 0 10px 0;">
        <?php if ($totalPages > 1): ?>

          <?php if ($page > 1): ?>
            <a href="?mode=<?= urlencode($mode) ?>&page=1" style="display:inline-block; padding:8px 12px; margin:3px; background:#2c2c2c; color:#fff; text-decoration:none">
              <?= htmlspecialchars(om_t("В начало", "First")) ?>
            </a>
          <?php endif; ?>

          <?php
          $startPage = $page - 2;
          $endPage = $page + 2;
          if ($startPage < 1) $startPage = 1;
          if ($endPage > $totalPages) $endPage = $totalPages;

          for ($i = $startPage; $i <= $endPage; $i++):
          ?>
            <a href="?mode=<?= urlencode($mode) ?>&page=<?= $i ?>" style="display:inline-block; padding:8px 12px; margin:3px; background:<?= ($i == $page ? '#4a4a4a' : '#2c2c2c') ?>; color:#fff; text-decoration:none;">
              <?= $i ?>
            </a>
          <?php endfor; ?>

          <?php if ($page < $totalPages): ?>
            <a href="?mode=<?= urlencode($mode) ?>&page=<?= $totalPages ?>" style="display:inline-block; padding:8px 12px; margin:3px; background:#2c2c2c; color:#fff; text-decoration:none;">
              <?= htmlspecialchars(om_t("В конец", "Last")) ?>
            </a>
          <?php endif; ?>

          <div style="color:#bdbdbd; font-size:12px; margin-top:8px;">
            <?= htmlspecialchars(om_t("Страница", "Page")) ?> <?= $page ?> <?= htmlspecialchars(om_t("из", "of")) ?> <?= $totalPages ?>
          </div>

        <?php endif; ?>
      </div>
    </section>
  </main>
  <?php render_language_switcher(); ?>

  <div class="footer">
    <p>OldMarket &copy; 2025-2026</p>
  </div>
</body>
</html>
