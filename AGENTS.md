# AGENTS.md

Этот файл описывает текущее состояние проекта `VKR_puml` для следующих агентов и разработчиков. Ориентируйся на этот документ как на краткую рабочую карту проекта, но проверяй фактическое состояние кода перед изменениями.

## 1. Назначение проекта

Проект - Windows desktop-прототип для анализа целостности архитектурных описаний на PlantUML.

Текущий фокус:
- загрузка локальных `.puml` файлов;
- загрузка `.puml` файлов из публичного HTTPS Git-репозитория;
- ручное назначение типа диаграммы;
- построение общей модели проекта;
- базовый анализ согласованности между class и sequence, включая наличие классов, наличие операций, запрет вызова abstract-операций и проверку видимости операций;
- формирование отчета;
- preview диаграммы внутри приложения.

Что еще не реализовано:
- persistence project file между запусками;
- приватные Git-репозитории, SSH, токены и выбор ветки в Git-загрузке;
- полный набор правил валидации для всех типов диаграмм;
- полноценная упаковка в `.exe`.

## 2. Технологический стек

- Язык: Python 3.13+
- GUI: PySide6
- Тесты: `unittest`
- Рендер preview: PlantUML + Graphviz
- Git-загрузка: системный `git.exe` через `subprocess`
- Локальный launcher: `run_app.bat`

См. [pyproject.toml](./pyproject.toml).

## 3. Структура проекта

Ключевые директории:

- `app/presentation/`
  - GUI-слой
  - главное окно: `app/presentation/main_window.py`
  - preview-диалог: `app/presentation/dialogs/preview_dialog.py`

- `app/application/`
  - orchestration/use-case services
  - анализ: `app/application/services/analysis_service.py`
  - preview: `app/application/services/preview_service.py`
  - Git-импорт: `app/application/services/git_import_service.py`

- `app/domain/`
  - независимое аналитическое ядро
  - project model: `app/domain/project/models.py`
  - parsing: `app/domain/parsing/`
  - merge: `app/domain/merge/`
  - validation: `app/domain/validation/`
  - reporting: `app/domain/reporting/`

- `app/infrastructure/`
  - файловое чтение: `app/infrastructure/filesystem/file_reader.py`
  - экспорт отчета: `app/infrastructure/export/report_exporter.py`
  - bundled renderer backend: `app/infrastructure/rendering/backends.py`
  - Git adapter: `app/infrastructure/git/repository_loader.py`

- `app/bootstrap/`
  - фабрика зависимостей и entrypoint:
  - `app/bootstrap/app_factory.py`
  - `app/bootstrap/entrypoint.py`

- `tests/`
  - `tests/unit/`
  - `tests/integration/`
  - `tests/gui/`

- `tools/`
  - bundled tools для preview:
  - `tools/plantuml/plantuml.jar`
  - `tools/graphviz/.../bin/dot.exe`

- `.vkr_puml_git_cache/`
  - runtime cache для свежих clone Git-репозиториев
  - директория игнорируется git-ом и не должна попадать в коммиты/дистрибутив как исходный код проекта

## 4. Архитектурные принципы

### 4.1 Layered подход

Слои проекта разделены явно:

- `presentation`
  - только UI
  - не должен содержать правил анализа, Git clone-логики или renderer-логики

- `application`
  - координация сценариев
  - связывает UI/use-case с domain и infrastructure
  - не должен содержать доменную логику правил

- `domain`
  - ядро анализа
  - не должно зависеть от PySide6, renderer, Git или persistence

- `infrastructure`
  - адаптеры к файловой системе, renderer, export и системному Git

### 4.2 Реальный приоритет проекта

Главный приоритет текущей реализации:
- сначала аналитическое ядро;
- затем preview;
- затем удобные источники загрузки диаграмм, включая Git;
- persistence пока не добавлен.

Если меняешь проект, не размывай это разделение без явной причины.

## 5. Что сейчас реально реализовано

### 5.1 Загрузка локальных файлов и проектная модель

Поддерживается:
- загрузка нескольких локальных `.puml`;
- удаление файлов из текущей сессии;
- назначение типа диаграммы через GUI;
- статус файла:
  - `incomplete`
  - `ready`
  - `error`

Источник истины:
- `app/domain/project/models.py`
- `app/application/services/analysis_service.py`

### 5.2 Загрузка диаграмм из Git

Git-загрузка уже реализована как MVP.

Поведение:
- пользователь нажимает `Загрузить из Git`;
- вводит публичный HTTPS URL Git-репозитория;
- приложение вычисляет стабильную cache-папку `.vkr_puml_git_cache/<url_hash>/`;
- при каждой загрузке этого URL приложение удаляет соответствующую cache-папку и делает свежий `git clone`;
- `pull`, `fetch`, `reset`, merge-обновление и выбор ветки не используются;
- после clone приложение рекурсивно находит все `.puml`;
- найденные файлы загружаются в обычную таблицу документов;
- типы диаграмм пользователь назначает вручную;
- лишние найденные файлы пользователь удаляет из текущей сессии через существующую кнопку `Удалить`.

Ограничения:
- поддерживаются только публичные HTTPS URL;
- SSH, приватные репозитории, токены и пароли в UI не поддерживаются;
- branch selector не реализован, используется default branch репозитория;
- отдельного диалога выбора найденных `.puml` нет;
- Git должен быть доступен как системная команда `git`.

Ключевые файлы:
- `app/application/services/git_import_service.py`
- `app/infrastructure/git/repository_loader.py`
- `app/presentation/main_window.py`
- `app/bootstrap/app_factory.py`

Практически важно:
- Git-адаптер перед удалением проверяет, что удаляемая директория находится внутри `.vkr_puml_git_cache`;
- cache-директория добавлена в `.gitignore`;
- Git-логика не должна переезжать в `domain`.

### 5.3 Поддерживаемые типы диаграмм

В enum перечислены все типы из требований, но в анализе сейчас реально подключены только:
- `CLASS`
- `SEQUENCE`

Подключение parser-ов см. в:
- `app/application/services/analysis_service.py`

### 5.4 Парсинг

Сейчас реализованы:
- `ClassDiagramParser`
- `SequenceDiagramParser`

Они живут в:
- `app/domain/parsing/parsers.py`

`ClassDiagramParser` сейчас извлекает:
- классы;
- атрибуты;
- операции;
- сигнатуру операции;
- visibility операции:
  - `+` -> `public`
  - `#` -> `protected`
  - `-` -> `private`
  - без маркера -> `unknown`
- признак abstract-операции только по явному маркеру `{abstract}` перед именем операции.

Важно:
- abstract class/interface как контекст abstract-операций сейчас не интерпретируется;
- наследование для правил visibility сейчас не парсится;
- `protected` в текущей проверке трактуется строго: внешний вызов из другого класса запрещен.

Lexer:
- есть упрощенный построчный lexer в `app/domain/parsing/lexer.py`
- он используется как внутренний этап parser pipeline

### 5.5 Merge

Текущая merge-логика:
- объединение class-диаграмм в общую модель;
- merge новых атрибутов и новых операций;
- `merge conflict` при одинаковом имени метода и разной сигнатуре;
- `duplicate declaration warning`, если класс повторен без новых данных;
- skeleton + full class считается допустимым дополнением.

Источник истины:
- `app/domain/merge/merger.py`

### 5.6 Validation rules

Сейчас реально включены четыре правила:

- `MissingClassRule`
  - sequence participant должен разрешаться в известный класс

- `MissingOperationRule`
  - вызванная операция должна существовать у целевого класса

- `AbstractOperationCallRule`
  - sequence message не должен вызывать операцию, помеченную `{abstract}` на class-диаграмме

- `OperationVisibilityRule`
  - sequence message не должен вызывать `private` или `protected` операцию другого класса
  - self-call внутри того же класса разрешен
  - `public` и `unknown` visibility не считаются нарушением

Источник истины:
- `app/domain/validation/rules.py`

Правила подключаются в:
- `app/application/services/analysis_service.py`

Не предполагается, что остальные проверки уже есть только потому, что они были в плане.

### 5.7 Report

Есть текстовый отчет с:
- summary;
- errors;
- warnings;
- merge issues;
- найденными сущностями.

Источник истины:
- `app/domain/reporting/models.py`
- `app/infrastructure/export/report_exporter.py`

### 5.8 Preview

Preview уже реализован.

Поведение:
- при выборе файла и нажатии `Просмотреть` вызывается `DiagramPreviewService`;
- если renderer доступен, показывается PNG;
- если renderer недоступен, показывается read-only текст `.puml`.

Ключевые файлы:
- `app/application/services/preview_service.py`
- `app/presentation/dialogs/preview_dialog.py`
- `app/infrastructure/rendering/backends.py`

## 6. Bundled tools и preview "из коробки"

Preview спроектирован так, чтобы работать без настройки системного `PATH`, если рядом с проектом есть `tools/`.

Текущий порядок поиска renderer-инструментов:

1. bundled tools внутри проекта;
2. затем системные утилиты.

Что ищется:
- PlantUML:
  - `tools/plantuml/plantuml.jar`
  - `tools/plantuml.exe`
  - системный `plantuml`

- Graphviz:
  - любой `dot.exe` внутри `tools/graphviz/**`
  - затем системный `dot`

- Java:
  - системный `java`
  - затем `tools/jre/bin/java.exe` если будет добавлен позже

Важно:
- preview сейчас зависит от содержимого папки `tools/`
- если дистрибутив отдается пользователю, папка `tools/` должна ехать вместе с приложением

## 7. Запуск проекта

### Быстрый запуск

Используй:

```bat
run_app.bat
```

Launcher:
- ищет `.venv`, если она есть;
- иначе использует системный Python;
- проверяет наличие `PySide6`;
- запускает `app.bootstrap.entrypoint`.

### Прямой запуск из консоли

```powershell
python -m app.bootstrap.entrypoint
```

Для Git-загрузки дополнительно нужен установленный и доступный из процесса `git`.

## 8. Тесты и обязательная проверка

Основной тестовый набор:

- unit:
  - `tests/unit/test_domain_core.py`
  - `tests/unit/test_preview_service.py`
  - `tests/unit/test_git_repository_loader.py`

- integration:
  - `tests/integration/test_analysis_flow.py`
  - `tests/integration/test_git_import_flow.py`

- gui:
  - `tests/gui/test_main_window.py`

Перед завершением работы по коду запускай:

```powershell
python -m unittest discover -s tests -v
python -m compileall app tests
```

Если менялся preview, дополнительно полезно проверить реальный вызов preview service, а не только моки/двойники.

Если менялась Git-загрузка, проверь:
- HTTPS URL validation;
- стратегию `delete cache dir -> fresh git clone`;
- запрет удаления вне `.vkr_puml_git_cache`;
- рекурсивный поиск `.puml`;
- GUI-сценарий загрузки и удаления лишних импортированных строк.

## 9. Известные ограничения

- Persistence project file пока отсутствует.
- Реальный анализ реализован только для class + sequence.
- Формально в GUI есть список всех типов диаграмм, но parser-ы не реализованы для большинства из них.
- Activity-диаграммы пока не участвуют в semantic pipeline и не проверяются на соответствие class-диаграммам.
- Abstract-операции распознаются только по `{abstract}` непосредственно перед операцией.
- Visibility-проверка не учитывает наследование: `protected` сейчас запрещен для любого внешнего вызова из другого класса.
- Git-загрузка поддерживает только публичные HTTPS репозитории.
- Git-загрузка импортирует все найденные `.puml` рекурсивно; фильтр по подпапке и диалог выбора файлов пока отсутствуют.
- Git-загрузка не поддерживает SSH, токены, приватные репозитории и выбор ветки.
- Нет packaging-сборки в `.exe`.

## 10. Практические правила для следующих агентов

- Не утверждай, что "тип диаграммы поддержан", если для него нет parser-а и semantic pipeline.
- Не добавляй бизнес-логику в GUI-слой.
- Не встраивай renderer-логику в domain.
- Не встраивай Git clone/update-логику в domain.
- Не ломай bundled-tools сценарий preview.
- Не меняй стратегию Git update на `pull`/`fetch`/`reset` без явного решения: текущий MVP намеренно использует удаление cache-папки и свежий clone.
- Если меняешь удаление cache-папок, сохраняй защиту: удалять можно только директории внутри `.vkr_puml_git_cache`.
- Если меняешь статус/таблицу файлов в GUI, учитывай уже исправленный баг:
  - нельзя бездумно пересобирать всю таблицу из обработчика `QComboBox`, это уже приводило к артефактам строк и неправильному статусу.
- Если меняешь русские строки UI, проверяй отображение в реальном окне.
  - В некоторых выводах через shell видна порча кодировки; не делай вывод, что GUI тоже обязательно сломан. Проверяй фактическое поведение приложения.

## 11. Рекомендуемые следующие шаги

Наиболее логичные продолжения проекта:

1. добавить persistence project file;
2. добавить фильтр/выбор файлов для Git-импорта;
3. добавить parser-ы для других типов диаграмм, в первую очередь activity, если нужно правило "класс из activity должен быть на class-диаграмме";
4. расширить validation rules с учетом новых semantic data;
5. подготовить packaging в `.exe` с включением `tools/`;
6. нормализовать пользовательские русские строки и проверить кодировку UI по всему проекту.
