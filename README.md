# FastWordQuery (Anki 26+)

本仓库 fork 自 [sirius-fan/FastWordQuery](https://github.com/sirius-fan/FastWordQuery)（原项目为 [sth2018/FastWordQuery](https://github.com/sth2018/FastWordQuery)）。原插件支持到 Anki 24.04，这里只修了几处兼容性问题，让它能在 Anki 26.05+（Qt6 / Python 3.13）上继续用。功能和代码都是原作者的，感谢他们。

改动就三处：

- `Qt.WaitCursor` → `Qt.CursorShape.WaitCursor`
- Anki 26 移除的旧钩子 `browser.setupMenus`、`EditorWebView.contextMenuEvent` 换成对应的 `gui_hooks` 钩子
- 被移除的 `note.model()` 换成 `note.note_type()`

安装：把 `src` 文件夹复制到 Anki 插件目录（Tools → Add-ons → View Files），文件夹名随意。

注：百词斩接口已被官方关闭，查不到内容，请改用有道、剑桥等其它词典。

A fork of sirius-fan/FastWordQuery with three small compatibility fixes for Anki 26.05+ (Qt6 / Python 3.13). All credit goes to the original authors. Install by copying the `src` folder into your Anki add-ons folder. The Baicizhan service has been shut down; use Youdao or Cambridge instead.

---

以下为原项目 README（未改动）/ Original README below, unchanged:

# [dev] FastWordQuery_
**没改完，慢慢来**

适配pyqt6

适配anki新api

修改失效词典

修复css文件不能载入的问题（暂时有效）（  [问题来源](https://github.com/ankitects/anki/blob/main/ts/editor/plain-text-input/remove-prohibited.ts#L14) & [解释](https://forums.ankiweb.net/t/how-to-add-external-css-in-a-field/17838/9) ）
## 使用
- **自动：** 使用安装码 **103636257** （有时没有下面的方法更新及时）

或者

- **手动：** 复制src文件夹到插件文件夹即可，也可将其重命名为fastwq，啥都行。



# ENG


Adapt to pyqt6

Adapt to anki new api

Modify invalid dictionary

Fix the problem that the css file cannot be loaded (temporarily valid) ([problem source](https://github.com/ankitects/anki/blob/main/ts/editor/plain-text-input/remove-prohibited.ts#L14) & [Explanation](https://forums.ankiweb.net/t/how-to-add-external-css-in-a-field/17838/9) )
## Use
- **Automatic:** Use the installation code **103636257**

or
  
- **Manual:**  Copy the src folder to the plugin folder, or rename it to fastwq, whatever.


# -------------------


# FastWordQuery Addon For Anki

  [Supported Dictionaries](docs/services.md)

  [为单词添加真人发音（朗文mdx词典）](docs/get_mdx_ldoce6_sounds.md)



## Features

This addon query words definitions or examples etc. fields from local or online dictionaries to fill into the Anki note.  
It forks from [WordQuery](https://github.com/finalion/WordQuery), added **multi-thread** feature, improve stability, and some other features.

  - Querying Words and Making Cards, IMMEDIATELY!
  - Support querying in mdx and stardict dictionaries.
  - Support querying in web dictionaries.
  - Support **Multi-Thread** to query faster.

## Install

   1. Just copy the src folder to the plugin folder, or rename it to fastwq, whatever.



## Setting

### Shortcut
  1. Click Menu **"Tools -> Add-ons -> FastWQ -> Edit..."**  
      ![](screenshots/setting_menu.png)
  2. Edit the code and click **Save**  
      ![](screenshots/setting_shortcut.png)

### Config
  1. In Browser window click menu **"FastWQ -> Options"**  
      ![](screenshots/setting_config_01.png)

  2. Click **Settings** button in the Options window  
      ![](screenshots/setting_config_02.png)  
      - **Force Updates of all fields** : Update all fields even if it's None
      - **Ignore Accents** : Ignore accents symbol of word in querying
      - **Auto check new version** : Check new version at startup
      - **Number of Threads** : The number of threads running at the same time
  
  
## Usage

### Set the query fields

  1. Click menu **"Tools ->  FastWQ"**, or in Browser window click menu **"FastWQ -> Options"**
  2. Select note type  
      ![](screenshots/options_01.png)
  3. Select Dictionary  
      ![](screenshots/options_02.png)
  4. Select Fields  
      ![](screenshots/options_03.png)
  5. Click **OK** button  

### 'Browser' Window
  1. Select single or multiple words, click menu **"FastWQ -> Query Selected"** or press shortcut Default is **Ctrl+Q**.  
      ![](screenshots/options_04.png)
  2. Waiting query finished  
      ![](screenshots/use_01.png)
  
### 'Add' Window
  1. Click Add button in Browser window, open Add window  
      ![](screenshots/use_02.png)
  2. Edit key field and click Query button  
      ![](screenshots/use_03.png)


## Other Projects Used
  - [mdict-query](https://github.com/mmjang/mdict-query)
  - [pystardict](https://github.com/lig/pystardict)
  - [WordQuery](https://github.com/finalion/WordQuery)
  - [AnkiHub](https://github.com/dayjaby/AnkiHub)
  - [snowball_py](https://github.com/shibukawa/snowball_py)
