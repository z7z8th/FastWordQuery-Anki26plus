# FastWordQuery Addon For Anki 26+

## What's new

* Support Anki 26+.
* Support Querying 10K+ words in multi-process.(File descriptor leak fixed.)
* Replaced QThread with Multi-process to achieve **TRUE** concurrent query.
* Fixed LDOCE6 voice match. LDOCE6 add match MDX dict by file name in addition to dict title.
* Replace some regex match with html parser to be more accurate.
* Replace CSS regex wrapping with CSS parser wrapping to avoid corrupted output.
* Upgraded to mdict-utils version 2025 Jan 2.

## Guides

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

- Just copy the src folder to Anki's plugin folder（Tools → Add-ons → View Files）, or rename it to fastwq, whatever.
- 把 `src` 文件夹复制到 Anki 插件目录（Tools → Add-ons → View Files），也可将其重命名为fastwq，文件夹名随意。

## Setting

### Shortcut

  1. Click Menu **"Tools -> Add-ons -> FastWQ -> View Files..."**
     Edit `fastwq/__init__.py`
  2. Edit the code and click **Save**  

      ```python
      shortcut = ('Ctrl+Alt' if is_mac else 'Ctrl') + '+Q'
      ```

### Config

  1. In Browser window click menu **"FastWQ -> Options"**  
      ![Config 1](screenshots/setting_config_01.png)

  2. Click **Settings** button in the Options window  
      ![Settings](screenshots/setting_config_02.png)  
      - **Force Updates of all fields** : Update all fields even if it's None
      - **Ignore Accents** : Ignore accents symbol of word in querying
      - **Auto check new version** : Check new version at startup
      - **Number of Threads** : The number of threads running at the same time

## Usage

### Set the query fields

  1. Click menu **"Tools ->  FastWQ"**, or in Browser window click menu **"FastWQ -> Options"**
  2. Select note type  
      ![Choose Note Type](screenshots/options_01.png)
  3. Select Dictionary  
      ![Select Dictionary](screenshots/options_02.png)
  4. Select Fields  
      ![Select Fields](screenshots/options_03.png)
  5. Click **OK** button  

### 'Browser' Window

  1. Select single or multiple words, click menu **"FastWQ -> Query Selected"** or press shortcut Default is **Ctrl+Q**.  
      ![Query Selected Words](screenshots/options_04.png)
  2. Waiting query finished  
      ![Waiting query finished](screenshots/use_01.png)
  
### 'Add' Window

  1. Click Add button in Browser window, open Add window  
      ![Add Card and Query](screenshots/use_02.png)
  2. Edit key field and click Query button  
      ![QueryResult](screenshots/use_03.png)

## Other Projects Used

- [aiJinn/FastWordQuery-Anki26plus](https://github.com/GaiJinn/FastWordQuery-Anki26plus)
- [sirius-fan/FastWordQuery](https://github.com/sirius-fan/FastWordQuery)
- [sth2018/FastWordQuery](https://github.com/sth2018/FastWordQuery)
- [mdict-query](https://github.com/mmjang/mdict-query)
- [pystardict](https://github.com/lig/pystardict)
- [WordQuery](https://github.com/finalion/WordQuery)
- [AnkiHub](https://github.com/dayjaby/AnkiHub)
- [snowball_py](https://github.com/shibukawa/snowball_py)
