# НЦФУ Android (TWA)

APK-обёртка над [app.enexus.isabelline.xyz](https://app.enexus.isabelline.xyz) через Trusted Web Activity.

## Требования

- Android Studio Hedgehog или новее / JDK 17+
- Готовый `ncfu.keystore` в корне проекта

## 1. Добавить assetlinks.json на сервер

Скопируй файл `assetlinks.json` на сервер:

```bash
sudo mkdir -p /var/www/html/.well-known
# или в папку Next.js проекта:
cp assetlinks.json /opt/ncfu/web/public/.well-known/assetlinks.json
```

Настрой nginx чтобы отдавал файл:

```nginx
location /.well-known/assetlinks.json {
    default_type application/json;
    add_header Access-Control-Allow-Origin *;
}
```

Проверь что файл доступен:
```
https://app.enexus.isabelline.xyz/.well-known/assetlinks.json
```

## 2. Сборка APK

```bash
# Debug (для тестирования, не требует keystore)
./gradlew assembleDebug

# Release (подписанный APK)
export KEYSTORE_PASSWORD=твой_пароль
export KEY_PASSWORD=твой_пароль
./gradlew assembleRelease

# APK будет в:
# app/build/outputs/apk/release/app-release.apk
```

## 3. Иконки

Замени заглушки в `app/src/main/res/mipmap-*/` на реальные:

| Папка             | Размер  |
|-------------------|---------|
| mipmap-mdpi       | 48×48   |
| mipmap-hdpi       | 72×72   |
| mipmap-xhdpi      | 96×96   |
| mipmap-xxhdpi     | 144×144 |
| mipmap-xxxhdpi    | 192×192 |

Быстрый способ — через [Android Asset Studio](https://romannurik.github.io/AndroidAssetStudio/icons-launcher.html).

## Как работает TWA

1. Пользователь открывает APK
2. Android проверяет `assetlinks.json` на сервере
3. Если fingerprint совпадает → Chrome открывает сайт **без адресной строки**
4. Выглядит как нативное приложение
5. Оффлайн-кеш работает через Service Worker сайта

## Структура

```
ncfu-twa/
  app/
    src/main/
      java/xyz/isabelline/enexus/ncfu/
        LauncherActivity.java   ← точка входа, запускает TWA
      res/
        values/strings.xml
        values/themes.xml
      AndroidManifest.xml
    build.gradle
  assetlinks.json               ← положить на сервер в /.well-known/
  build.gradle
  settings.gradle
  gradle.properties
  README.md
```
