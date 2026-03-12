#!/usr/bin/env bash
# run.sh — установка и запуск на подключённом Android устройстве/эмуляторе
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APK="$SCRIPT_DIR/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE="xyz.isabelline.enexus.ncfu.debug"

# Фикс: используем только ANDROID_HOME
export ANDROID_HOME="${ANDROID_HOME:-/home/archlinux/android-sdk}"
unset ANDROID_SDK_ROOT

# Проверяем adb
if ! command -v adb &>/dev/null; then
  echo "❌ adb не найден. Установи Android SDK Platform Tools."
  exit 1
fi

# Проверяем устройство
DEVICE=$(adb devices | grep -v "List" | grep "device$" | head -1 | cut -f1)
if [ -z "$DEVICE" ]; then
  echo "❌ Нет подключённых устройств. Подключи телефон или запусти эмулятор."
  exit 1
fi
echo "📱 Устройство: $DEVICE"

# Собираем debug если APK не существует
if [ ! -f "$APK" ]; then
  echo "🔨 Собираем debug APK..."
  cd "$SCRIPT_DIR"
  ./gradlew assembleDebug
fi

echo "📦 Устанавливаем..."
adb -s "$DEVICE" install -r "$APK"

echo "🚀 Запускаем..."
adb -s "$DEVICE" shell am start -n "$PACKAGE/xyz.isabelline.enexus.ncfu.LauncherActivity"

echo "✅ Готово!"
