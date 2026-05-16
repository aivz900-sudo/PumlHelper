import unittest

from app.domain.merge.merger import MergeSeverity, ModelMerger
from app.domain.parsing.parsers import ClassDiagramParser, SequenceDiagramParser
from app.domain.project.models import DiagramDocument, DiagramType, DocumentStatus
from app.domain.validation.engine import ValidationEngine
from app.domain.validation.rules import (
    AbstractOperationCallRule,
    MissingClassRule,
    MissingOperationRule,
    OperationVisibilityRule,
)


class DiagramDocumentTests(unittest.TestCase):
    def test_document_without_type_is_incomplete(self) -> None:
        document = DiagramDocument(path="test.puml", source_text="@startuml\n@enduml")

        self.assertEqual(document.status, DocumentStatus.INCOMPLETE)
        self.assertFalse(document.ready_for_analysis)


class ClassDiagramParserTests(unittest.TestCase):
    def test_parse_class_diagram_builds_class_nodes(self) -> None:
        parser = ClassDiagramParser()
        source = """
        @startuml
        class UserService {
          +login(username, password)
          -token: str
        }
        @enduml
        """
        document = DiagramDocument(
            path="class.puml",
            source_text=source,
            diagram_type=DiagramType.CLASS,
        )

        parsed = parser.parse(document)

        self.assertEqual(parsed.diagram_type, DiagramType.CLASS)
        self.assertEqual(len(parsed.ast.classes), 1)
        class_node = parsed.ast.classes[0]
        self.assertEqual(class_node.name, "UserService")
        self.assertEqual(len(class_node.operations), 1)
        self.assertEqual(len(class_node.attributes), 1)

    def test_parse_class_diagram_preserves_operation_visibility_and_abstract_marker(self) -> None:
        parser = ClassDiagramParser()
        source = """
        @startuml
        class UserService {
          +login()
          #refresh()
          -resetToken()
          ping()
          {abstract} loadProfile()
        }
        @enduml
        """
        document = DiagramDocument(
            path="class.puml",
            source_text=source,
            diagram_type=DiagramType.CLASS,
        )

        parsed = parser.parse(document)
        operations = parsed.semantic_fragment.classes["UserService"].operations

        self.assertEqual(operations["login"].visibility, "public")
        self.assertEqual(operations["refresh"].visibility, "protected")
        self.assertEqual(operations["resetToken"].visibility, "private")
        self.assertEqual(operations["ping"].visibility, "unknown")
        self.assertTrue(operations["loadProfile"].is_abstract)
        self.assertEqual(operations["loadProfile"].visibility, "unknown")


class SequenceDiagramParserTests(unittest.TestCase):
    def test_parse_sequence_diagram_builds_scenario(self) -> None:
        parser = SequenceDiagramParser()
        source = """
        @startuml
        participant client:Client
        participant service:UserService
        client -> service: login(username, password)
        @enduml
        """
        document = DiagramDocument(
            path="sequence.puml",
            source_text=source,
            diagram_type=DiagramType.SEQUENCE,
        )

        parsed = parser.parse(document)

        self.assertEqual(parsed.diagram_type, DiagramType.SEQUENCE)
        self.assertEqual(len(parsed.ast.participants), 2)
        self.assertEqual(len(parsed.ast.messages), 1)
        self.assertEqual(parsed.ast.messages[0].operation_name, "login")


class MergeTests(unittest.TestCase):
    def setUp(self) -> None:
        parser = ClassDiagramParser()
        self.merger = ModelMerger()
        self.base_document = DiagramDocument(
            path="base.puml",
            source_text="""
            @startuml
            class UserService {
              +login(username, password)
            }
            @enduml
            """,
            diagram_type=DiagramType.CLASS,
        )
        self.base_fragment = parser.parse(self.base_document).semantic_fragment

    def test_merge_ok_when_class_definitions_are_complementary(self) -> None:
        parser = ClassDiagramParser()
        additional_document = DiagramDocument(
            path="extra.puml",
            source_text="""
            @startuml
            class UserService {
              -token: str
              +logout()
            }
            @enduml
            """,
            diagram_type=DiagramType.CLASS,
        )
        additional_fragment = parser.parse(additional_document).semantic_fragment

        model = self.merger.merge([self.base_fragment, additional_fragment])

        self.assertIn("UserService", model.classes)
        self.assertEqual(model.operations_index["UserService"], {"login", "logout"})
        self.assertEqual(model.merge_issues, [])

    def test_merge_conflict_when_method_signature_differs(self) -> None:
        parser = ClassDiagramParser()
        conflicting_document = DiagramDocument(
            path="conflict.puml",
            source_text="""
            @startuml
            class UserService {
              +login(username)
            }
            @enduml
            """,
            diagram_type=DiagramType.CLASS,
        )
        conflicting_fragment = parser.parse(conflicting_document).semantic_fragment

        model = self.merger.merge([self.base_fragment, conflicting_fragment])

        self.assertEqual(len(model.merge_issues), 1)
        self.assertEqual(model.merge_issues[0].severity, MergeSeverity.CONFLICT)

    def test_duplicate_declaration_warning_when_no_new_data(self) -> None:
        parser = ClassDiagramParser()
        duplicate_document = DiagramDocument(
            path="duplicate.puml",
            source_text="""
            @startuml
            class UserService {
              +login(username, password)
            }
            @enduml
            """,
            diagram_type=DiagramType.CLASS,
        )
        duplicate_fragment = parser.parse(duplicate_document).semantic_fragment

        model = self.merger.merge([self.base_fragment, duplicate_fragment])

        self.assertEqual(len(model.merge_issues), 1)
        self.assertEqual(model.merge_issues[0].severity, MergeSeverity.WARNING)


class ValidationTests(unittest.TestCase):
    def test_missing_class_rule_reports_unknown_sequence_participant_class(self) -> None:
        class_parser = ClassDiagramParser()
        sequence_parser = SequenceDiagramParser()
        merger = ModelMerger()

        class_doc = DiagramDocument(
            path="class.puml",
            source_text="""
            @startuml
            class UserService {
              +login()
            }
            @enduml
            """,
            diagram_type=DiagramType.CLASS,
        )
        sequence_doc = DiagramDocument(
            path="sequence.puml",
            source_text="""
            @startuml
            participant client:Client
            participant service:MissingService
            client -> service: login()
            @enduml
            """,
            diagram_type=DiagramType.SEQUENCE,
        )

        model = merger.merge(
            [
                class_parser.parse(class_doc).semantic_fragment,
                sequence_parser.parse(sequence_doc).semantic_fragment,
            ]
        )
        issues = ValidationEngine([MissingClassRule()]).validate(model)

        self.assertEqual(len(issues), 2)
        self.assertTrue(any(issue.entity_name == "Client" for issue in issues))
        self.assertTrue(any(issue.entity_name == "MissingService" for issue in issues))

    def test_missing_operation_rule_reports_unknown_operation(self) -> None:
        class_parser = ClassDiagramParser()
        sequence_parser = SequenceDiagramParser()
        merger = ModelMerger()

        class_doc = DiagramDocument(
            path="class.puml",
            source_text="""
            @startuml
            class UserService {
              +login()
            }
            @enduml
            """,
            diagram_type=DiagramType.CLASS,
        )
        sequence_doc = DiagramDocument(
            path="sequence.puml",
            source_text="""
            @startuml
            participant service:UserService
            participant client:Client
            client -> service: logout()
            @enduml
            """,
            diagram_type=DiagramType.SEQUENCE,
        )

        model = merger.merge(
            [
                class_parser.parse(class_doc).semantic_fragment,
                sequence_parser.parse(sequence_doc).semantic_fragment,
            ]
        )
        issues = ValidationEngine([MissingClassRule(), MissingOperationRule()]).validate(model)

        self.assertTrue(any(issue.entity_name == "logout" for issue in issues))

    def test_abstract_operation_call_rule_reports_sequence_call_to_abstract_operation(self) -> None:
        model = self._build_model(
            class_source="""
            @startuml
            class UserService {
              {abstract} loadProfile()
            }
            class Client
            @enduml
            """,
            sequence_source="""
            @startuml
            participant client:Client
            participant service:UserService
            client -> service: loadProfile()
            @enduml
            """,
        )

        issues = ValidationEngine([AbstractOperationCallRule()]).validate(model)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].rule_id, "abstract-operation-call")
        self.assertEqual(issues[0].entity_name, "loadProfile")

    def test_operation_visibility_rule_reports_private_or_protected_external_call(self) -> None:
        model = self._build_model(
            class_source="""
            @startuml
            class UserService {
              -resetToken()
              #refresh()
            }
            class Client
            @enduml
            """,
            sequence_source="""
            @startuml
            participant client:Client
            participant service:UserService
            client -> service: resetToken()
            client -> service: refresh()
            @enduml
            """,
        )

        issues = ValidationEngine([OperationVisibilityRule()]).validate(model)

        self.assertEqual(len(issues), 2)
        self.assertTrue(all(issue.rule_id == "operation-visibility-violation" for issue in issues))
        self.assertEqual({issue.entity_name for issue in issues}, {"resetToken", "refresh"})

    def test_operation_visibility_rule_allows_public_external_call(self) -> None:
        model = self._build_model(
            class_source="""
            @startuml
            class UserService {
              +login()
            }
            class Client
            @enduml
            """,
            sequence_source="""
            @startuml
            participant client:Client
            participant service:UserService
            client -> service: login()
            @enduml
            """,
        )

        issues = ValidationEngine([OperationVisibilityRule()]).validate(model)

        self.assertEqual(issues, [])

    def test_operation_visibility_rule_allows_private_or_protected_self_call(self) -> None:
        model = self._build_model(
            class_source="""
            @startuml
            class UserService {
              -resetToken()
              #refresh()
            }
            @enduml
            """,
            sequence_source="""
            @startuml
            participant service:UserService
            service -> service: resetToken()
            service -> service: refresh()
            @enduml
            """,
        )

        issues = ValidationEngine([OperationVisibilityRule()]).validate(model)

        self.assertEqual(issues, [])

    def test_operation_visibility_rule_ignores_unknown_visibility(self) -> None:
        model = self._build_model(
            class_source="""
            @startuml
            class UserService {
              ping()
            }
            class Client
            @enduml
            """,
            sequence_source="""
            @startuml
            participant client:Client
            participant service:UserService
            client -> service: ping()
            @enduml
            """,
        )

        issues = ValidationEngine([OperationVisibilityRule()]).validate(model)

        self.assertEqual(issues, [])

    def _build_model(self, class_source: str, sequence_source: str):
        class_parser = ClassDiagramParser()
        sequence_parser = SequenceDiagramParser()
        merger = ModelMerger()
        class_doc = DiagramDocument(
            path="class.puml",
            source_text=class_source,
            diagram_type=DiagramType.CLASS,
        )
        sequence_doc = DiagramDocument(
            path="sequence.puml",
            source_text=sequence_source,
            diagram_type=DiagramType.SEQUENCE,
        )
        return merger.merge(
            [
                class_parser.parse(class_doc).semantic_fragment,
                sequence_parser.parse(sequence_doc).semantic_fragment,
            ]
        )


if __name__ == "__main__":
    unittest.main()
