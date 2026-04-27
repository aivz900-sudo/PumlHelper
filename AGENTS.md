# AGENTS.md

Этот файл описывает текущее состояние проекта `VKR_puml` для следующих агентов и разработчиков. Ориентируйся на этот документ как на краткую рабочую карту проекта, но проверяй фактическое состояние кода перед изменениями.

## 1. Назначение проекта

Проект — Windows desktop-прототип для анализа целостности архитектурных описаний на PlantUML.

Текущий фокус:
- загрузка `.puml` файлов;
- ручное назначение типа диаграммы;
- построение общей модели проекта;
- базовый анализ согласованности между class и sequence;
- формирование отчёта;
- preview диаграммы внутри приложения.

Что еще не реализовано:
- persistence project file между запусками;
- полный набор правил валидации для всех типов диаграмм;
- полноценная упаковка в `.exe`.

## 2. Технологический стек

- Язык: Python 3.13+
- GUI: PySide6
- Тесты: `unittest`
- Рендер preview: PlantUML + Graphviz
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

- `app/domain/`
  - независимое аналитическое ядро
  - project model: `app/domain/project/models.py`
  - parsing: `app/domain/parsing/`
  - merge: `app/domain/merge/`
  - validation: `app/domain/validation/`
  - reporting: `app/domain/reporting/`

- `app/infrastructure/`
  - файловое чтение: `app/infrastructure/filesystem/file_reader.py`
  - экспорт отчёта: `app/infrastructure/export/report_exporter.py`
  - bundled renderer backend: `app/infrastructure/rendering/backends.py`

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

## 4. Архитектурные принципы

### 4.1 Layered подход

Слои проекта разделены явно:

- `presentation`
  - только UI
  - не должен содержать правил анализа

- `application`
  - координация сценариев
  - не должен содержать доменную логику правил

- `domain`
  - ядро анализа
  - не должно зависеть от PySide6, renderer и persistence

- `infrastructure`
  - адаптеры к файловой системе, renderer, export

### 4.2 Реальный приоритет проекта

Главный приоритет текущей реализации:
- сначала аналитическое ядро;
- затем preview;
- persistence пока не добавлен.

Если меняешь проект, не размывай это разделение без явной причины.

## 5. Что сейчас реально реализовано

### 5.1 Загрузка и проектная модель

Поддерживается:
- загрузка нескольких `.puml`;
- удаление файлов из текущей сессии;
- назначение типа диаграммы через GUI;
- статус файла:
  - `incomplete`
  - `ready`
  - `error`

Источник истины:
- `app/domain/project/models.py`

### 5.2 Поддерживаемые типы диаграмм

В enum перечислены все типы из требований, но в анализе сейчас реально подключены только:
- `CLASS`
- `SEQUENCE`

Подключение parser-ов см. в:
- `app/application/services/analysis_service.py`

### 5.3 Парсинг

Сейчас реализованы:
- `ClassDiagramParser`
- `SequenceDiagramParser`

Они живут в:
- `app/domain/parsing/parsers.py`

Lexer:
- есть упрощённый построчный lexer в `app/domain/parsing/lexer.py`
- он используется как внутренний этап parser pipeline

### 5.4 Merge

Текущая merge-логика:
- объединение class-диаграмм в общую модель;
- merge новых атрибутов и новых операций;
- `merge conflict` при одинаковом имени метода и разной сигнатуре;
- `duplicate declaration warning`, если класс повторён без новых данных;
- skeleton + full class считается допустимым дополнением.

Источник истины:
- `app/domain/merge/merger.py`

### 5.5 Validation rules

Сейчас реально включены только два правила:

- `MissingClassRule`
  - sequence participant должен разрешаться в известный класс

- `MissingOperationRule`
  - вызванная операция должна существовать у целевого класса

Источник истины:
- `app/domain/validation/rules.py`

Не предполагается, что остальные проверки уже есть только потому, что они были в плане.

### 5.6 Report

Есть текстовый отчёт с:
- summary;
- errors;
- warnings;
- merge issues;
- найденными сущностями.

Источник истины:
- `app/domain/reporting/models.py`
- `app/infrastructure/export/report_exporter.py`

### 5.7 Preview

Preview уже реализован.

Поведение:
- при выборе файла и нажатии `Просмотреть` вызывается `DiagramPreviewService`;
- если renderer доступен, показывается PNG;
- если renderer недоступен, показывается read-only текст `.puml`.

Ключевые файлы:
- `app/application/services/preview_service.py`
- `app/presentation/dialogs/preview_dialog.py`
- `app/infrastructure/rendering/backends.py`

## 6. Bundled tools и preview “из коробки”

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
- если дистрибутив отдаётся пользователю, папка `tools/` должна ехать вместе с приложением

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

## 8. Тесты и обязательная проверка

Основной тестовый набор:

- unit:
  - `tests/unit/test_domain_core.py`
  - `tests/unit/test_preview_service.py`

- integration:
  - `tests/integration/test_analysis_flow.py`

- gui:
  - `tests/gui/test_main_window.py`

Перед завершением работы по коду запускай:

```powershell
python -m unittest discover -s tests -v
python -m compileall app tests
```

Если менялся preview, дополнительно полезно проверить реальный вызов preview service, а не только моки/двойники.

## 9. Известные ограничения

- Persistence project file пока отсутствует.
- Реальный анализ реализован только для class + sequence.
- Формально в GUI есть список всех типов диаграмм, но parser-и не реализованы для большинства из них.
- Нет packaging-сборки в `.exe`.
- Проект сейчас не находится в git-репозитории. Не предполагай наличие веток, commit history или worktree.

## 10. Практические правила для следующих агентов

- Не утверждай, что “тип диаграммы поддержан”, если для него нет parser-а и semantic pipeline.
- Не добавляй бизнес-логику в GUI-слой.
- Не встраивай renderer-логику в domain.
- Не ломай bundled-tools сценарий preview.
- Если меняешь статус/таблицу файлов в GUI, учитывай уже исправленный баг:
  - нельзя бездумно пересобирать всю таблицу из обработчика `QComboBox`, это уже приводило к артефактам строк и неправильному статусу.
- Если меняешь русские строки UI, проверяй отображение в реальном окне.
  - В некоторых выводах через shell видна порча кодировки; не делай вывод, что GUI тоже обязательно сломан. Проверяй фактическое поведение приложения.

## 11. Рекомендуемые следующие шаги

Наиболее логичные продолжения проекта:

1. добавить persistence project file;
2. расширить validation rules;
3. добавить parser-ы для других типов диаграмм;
4. подготовить packaging в `.exe` с включением `tools/`;
5. нормализовать пользовательские русские строки и проверить кодировку UI по всему проекту.
