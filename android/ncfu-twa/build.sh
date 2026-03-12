#!/usr/bin/env bash
# build.sh — сборка подписанного APK
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# Загружаем переменные из .env
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Файл .env не найден. Скопируй .env.example → .env и заполни пароли."
  exit 1
fi

export $(grep -v '^#' "$ENV_FILE" | xargs)

# Фикс: используем только ANDROID_HOME, убираем устаревший ANDROID_SDK_ROOT
export ANDROID_HOME="${ANDROID_HOME:-/home/archlinux/android-sdk}"
unset ANDROID_SDK_ROOT

echo "🔨 Сборка release APK..."
cd "$SCRIPT_DIR"
./gradlew assembleRelease

APK="app/build/outputs/apk/release/app-release.apk"
if [ -f "$APK" ]; then
  SIZE=$(du -sh "$APK" | cut -f1)
  echo ""
  echo "✅ Готово: $APK ($SIZE)"
else
  echo "❌ APK не найден — что-то пошло не так"
  exit 1
fi
