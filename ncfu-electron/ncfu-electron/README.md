# НЦФУ Desktop

Десктопное приложение — обёртка над [app.enexus.isabelline.xyz](https://app.enexus.isabelline.xyz).

## Стек

- **Electron 30** — оболочка
- **WebView** — отображает существующий Next.js сайт
- Кастомный titlebar (frameless window)
- Трей с быстрым доступом к расписанию
- Оффлайн-экран при отсутствии сети
- Сохранение сессии между запусками (`partition: persist:ncfu`)

## Установка и запуск

```bash
npm install
npm start
```

## Сборка

### Windows (NSIS installer + portable)
```bash
npm run dist:win
```

### Linux (AppImage + deb)
```bash
npm run dist:linux
```

### macOS (DMG)
```bash
npm run dist:mac
```

### Все платформы
```bash
npm run dist
```

Собранные файлы появятся в папке `dist/`.

## Иконки

Для корректной сборки нужны:

| Файл              | Размер   | Платформа       |
|-------------------|----------|-----------------|
| `assets/icon.png` | 256×256  | Linux           |
| `assets/icon.ico` | multi    | Windows         |
| `assets/icon.icns`| multi    | macOS           |

Конвертировать из PNG:
```bash
# ico (Windows) — через imagemagick
convert assets/icon.png -define icon:auto-resize=256,128,64,48,32,16 assets/icon.ico

# icns (macOS)
mkdir icon.iconset
sips -z 16 16   assets/icon.png --out icon.iconset/icon_16x16.png
sips -z 32 32   assets/icon.png --out icon.iconset/icon_32x32.png
sips -z 128 128 assets/icon.png --out icon.iconset/icon_128x128.png
sips -z 256 256 assets/icon.png --out icon.iconset/icon_256x256.png
iconutil -c icns icon.iconset -o assets/icon.icns
```

## Горячие клавиши

| Клавиша              | Действие          |
|----------------------|-------------------|
| `F5` / `Ctrl+R`      | Обновить страницу |
| `Ctrl+←`             | Назад             |
| `Ctrl+→`             | Вперёд            |
| `F12`                | DevTools          |
