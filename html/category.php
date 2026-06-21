<?php
require_once __DIR__ . '/auth_cookie.php';
require_once __DIR__ . '/site_ui.php';
require_once 'android_versions.php';

header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');

$auth = auth_user();
$categoryCode = isset($_GET['code']) ? trim($_GET['code']) : '';
$categoryTitle = 'Категория';
$categoryType = '';
$apps = [];
$topApps = [];
$errorText = '';

if ($categoryCode !== '') {
    $categoryResponse = api_get('/api/category/' . rawurlencode($categoryCode) . '/apps');
    $categoryData = $categoryResponse ? json_decode($categoryResponse, true) : [];

    if (is_array($categoryData) && isset($categoryData['category']) && isset($categoryData['apps']) && is_array($categoryData['apps'])) {
        $apps = $categoryData['apps'];
        $categoryTitle = $categoryData['category']['label'] ?? $categoryCode;
        $categoryType = !empty($categoryData['category']['is_game']) ? 'Игры' : 'Приложения';
        $topApps = $apps;
        usort($topApps, function ($a, $b) {
            $da = isset($a['downloads']) ? (int)$a['downloads'] : 0;
            $db = isset($b['downloads']) ? (int)$b['downloads'] : 0;
            if ($da === $db) return 0;
            return ($da < $db) ? 1 : -1;
        });
        $topApps = array_slice($topApps, 0, 10);
    } else {
        $errorText = 'Категория не найдена.';
    }
} else {
    $errorText = 'Не указана категория.';
}

$bannerResponse = api_get('/api/banners');
$banners = $bannerResponse ? json_decode($bannerResponse, true) : [];
if (!is_array($banners)) $banners = [];
?>
<!DOCTYPE html>
<html lang="<?= htmlspecialchars(om_lang()) ?>">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <title>OldMarket - <?= htmlspecialchars($categoryTitle) ?></title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
<?php render_site_header($auth, "index.php"); ?>
<div class="banner" id="banner"
     data-interval="5000"
     style="width:100%; text-align:center; overflow:hidden; cursor:pointer;">
  <?php if (!empty($banners)): ?>
    <a id="bannerLink" href="<?= htmlspecialchars($banners[0]['url'] ?? '') ?>" target="_blank" rel="noopener">
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
function searchApps() {
  var query = document.getElementById('searchInput').value.toLowerCase();
  var apps = document.getElementsByClassName('app');
  var i, appName;

  for (i = 0; i < apps.length; i++) {
    appName = apps[i].getElementsByClassName('app-title')[0].textContent.toLowerCase();
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
  var intervalAttr, tmp, i, im, idx;

  if (bannerWrap) {
    intervalAttr = bannerWrap.getAttribute('data-interval');
    tmp = parseInt(intervalAttr, 10);
    if (!isNaN(tmp) && tmp > 0) changeMs = tmp;
  }

  for (i = 0; i < BANNERS.length; i++) {
    if (BANNERS[i] && BANNERS[i].image) {
      im = new Image();
      im.src = 'http://94.156.115.120:5000/html/banners/' + BANNERS[i].image;
    }
  }

  idx = 0;

  function applyBanner(i) {
    var b = BANNERS[i] || {};
    var src = 'http://94.156.115.120:5000/html/banners/' + (b.image || '');
    var url;

    imgEl.src = src;

    if (linkEl) {
      url = (b.url || '').replace(/^\s+|\s+$/g, '');
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
</script>

<main>
  <section class="featured">
    <h2 style="color: white; text-align: center;"><?= htmlspecialchars(om_t("Популярные в", "Popular in")) ?> <?= htmlspecialchars($categoryTitle) ?></h2>
    <p style="color: white; text-align: center; margin-top: -10px;"><?= htmlspecialchars($categoryType) ?></p>

    <?php if ($errorText !== ''): ?>
      <div style="color: white; text-align: center; margin: 20px 0;">
        <?= htmlspecialchars($errorText) ?><br><br>
        <a href="categories.php" style="color: white;">Вернуться к категориям</a>
      </div>
    <?php else: ?>
      <div class="app-list">
        <div class="add">
          <img src="back.jpg" alt="<?= htmlspecialchars(om_t("Категории", "Categories")) ?>" width="190" class="button-image" onclick="window.location.href='categories.php'">
        </div>
        <?php foreach ($topApps as $app): ?>
        <div class="app" onclick="installApp(<?= (int)$app['id'] ?>)">
          <img src="http://94.156.115.120:5000/html/apps/<?= htmlspecialchars($app['icon']) ?>" width="55" alt="<?= htmlspecialchars($app['name']) ?>">
          <div class="app-info">
            <span class="app-title"><?= htmlspecialchars($app['name']) ?></span><br>
            <span><?= htmlspecialchars(om_t("Рейтинг", "Rating")) ?>: <?= htmlspecialchars($app['rating']) ?> ★</span><br>
            <span><?= htmlspecialchars(om_t("Скачиваний", "Downloads")) ?>: <?= htmlspecialchars($app['downloads']) ?></span><br>
            <span>Android <?= htmlspecialchars(apiToAndroidVersion($app['api'])) ?></span>
          </div>
        </div>
        <?php endforeach; ?>
      </div>

      <h2 style="color: white; text-align: center; margin-top: 30px;"><?= htmlspecialchars(om_t("Все в", "All in")) ?> <?= htmlspecialchars($categoryTitle) ?></h2>
      <div class="app-list">
        <?php foreach ($apps as $app): ?>
        <div class="app" onclick="installApp(<?= (int)$app['id'] ?>)">
          <img src="http://94.156.115.120:5000/html/apps/<?= htmlspecialchars($app['icon']) ?>" width="55" alt="<?= htmlspecialchars($app['name']) ?>">
          <div class="app-info">
            <span class="app-title"><?= htmlspecialchars($app['name']) ?></span><br>
            <span><?= htmlspecialchars(om_t("Рейтинг", "Rating")) ?>: <?= htmlspecialchars($app['rating']) ?> ★</span><br>
            <span><?= htmlspecialchars(om_t("Скачиваний", "Downloads")) ?>: <?= htmlspecialchars($app['downloads']) ?></span><br>
            <span>Android <?= htmlspecialchars(apiToAndroidVersion($app['api'])) ?></span>
          </div>
        </div>
        <?php endforeach; ?>
      </div>
    <?php endif; ?>
  </section>
</main>
<div class="footer">
  <p>OldMarket &copy; 2025-2026</p>
</div>
</body>
</html>
