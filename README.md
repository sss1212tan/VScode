<img width="858" alt="image" src="https://github.com/tanssscn/Label-Point/assets/57119006/a6905735-0a1f-4cf5-b6d7-9800260e9b98">

# Label Point

This project marks the typhoon eye, using Python Tkinter GUI library to achieve.

## 打包为可执行文件

使用pyinstaller工具

```bash
 pyinstaller  --onefile  -w -i myLabel.ico --clean myLabel.py
```

## 制作 mac dmg映像
进入到dist目录下
```bash
cd dist
```

使用create-dmg工具

```bash
create-dmg \
 --volname "myLabel" \
 --volicon "../myLabel.ico" \
 --window-pos 200 120 \
 --window-size 600 300 \
 --icon-size 100 \
 --icon "myLabel.app" 175 120 \
 --hide-extension "myLabel.app" \
 --app-drop-link 425 120 \
 "myLabel.dmg" \
"."
```
