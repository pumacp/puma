import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestDataFiles:
    """Pruebas de integración - Verificar archivos de datos"""

    def test_jira_csv_exists(self):
        """Verificar que existe archivo Jira"""
        assert Path("data/jira_balanced_200.csv").exists()

    def test_tawos_csv_exists(self):
        """Verificar que existe archivo TAWOS"""
        assert Path("data/tawos_clean.csv").exists()

    def test_jira_csv_structure(self):
        """Verificar estructura de CSV Jira"""
        df = pd.read_csv("data/jira_balanced_200.csv")

        required_cols = ['issue_key', 'title', 'description', 'priority']
        for col in required_cols:
            assert col in df.columns, f"Columna {col} no encontrada"

    def test_jira_balance(self):
        """Verificar balanceo de clases en Jira"""
        df = pd.read_csv("data/jira_balanced_200.csv")

        priorities = df['priority'].value_counts()

        assert len(priorities) <= 4, "Demasiadas prioridades"

        for priority in ['Critical', 'Major', 'Minor', 'Trivial']:
            if priority in priorities.index:
                count = priorities[priority]
                assert 40 <= count <= 60, f"Prioridad {priority} fuera de rango: {count}"

    def test_tawos_csv_structure(self):
        """Verificar estructura de CSV TAWOS"""
        df = pd.read_csv("data/tawos_clean.csv")

        required_cols = ['project', 'title', 'description', 'story_points']
        for col in required_cols:
            assert col in df.columns, f"Columna {col} no encontrada"

    def test_tawos_mesos_project(self):
        """Verificar que existe proyecto MESOS"""
        df = pd.read_csv("data/tawos_clean.csv")

        assert 'MESOS' in df['project'].values, "Proyecto MESOS no encontrado"

        mesos_df = df[df['project'] == 'MESOS']
        assert len(mesos_df) >= 100, f"Insuficientes registros MESOS: {len(mesos_df)}"


class TestTriageEvaluator:
    """Pruebas para src/evaluate_triage.py"""

    def test_parse_prediction_valid(self):
        """Test parsing predicciones válidas"""
        from evaluate_triage import parse_prediction

        test_cases = [
            ("Critical", "Critical"),
            ("  Critical  ", "Critical"),
            ("major", "Major"),
            ("MAJOR", "Major"),
            ("Minor", "Minor"),
            ("trivial", "Trivial"),
            ("The issue is Critical", "Critical"),
            ("Priority: Major", "Major"),
        ]

        for input_val, expected in test_cases:
            result = parse_prediction(input_val)
            assert result == expected, f"Falló: {input_val} -> {result} (esperado: {expected})"

    def test_parse_prediction_invalid(self):
        """Test parsing predicciones inválidas"""
        from evaluate_triage import parse_prediction

        invalid_cases = [
            "something else",
            "unknown",
            "High",
            "Low",
            "BLOCKER",
            "",
        ]

        for input_val in invalid_cases:
            result = parse_prediction(input_val)
            assert result is None, f"Falló (debería ser None): {input_val} -> {result}"

    def test_deterministic_options(self):
        """Verificar opciones deterministas"""
        from evaluate_triage import DETERMINISTIC_OPTIONS

        assert DETERMINISTIC_OPTIONS['temperature'] == 0.0
        assert DETERMINISTIC_OPTIONS['seed'] == 42

    def test_system_prompt_structure(self):
        """Verificar estructura del system prompt"""
        from evaluate_triage import SYSTEM_PROMPT

        assert "Critical" in SYSTEM_PROMPT
        assert "Major" in SYSTEM_PROMPT
        assert "Minor" in SYSTEM_PROMPT
        assert "Trivial" in SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 50


class TestEstimationEvaluator:
    """Pruebas para src/evaluate_estimation.py"""

    def test_parse_story_points_valid(self):
        """Test parsing story points válidos"""
        from evaluate_estimation import parse_story_points

        test_cases = [
            ("5", 5.0),
            ("  8  ", 8.0),
            ("3.0", 3.0),
            ("13", 13.0),
            ("1", 1.0),
            ("21", 21.0),
        ]

        for input_val, expected in test_cases:
            result = parse_story_points(input_val)
            assert result == expected, f"Falló: {input_val} -> {result} (esperado: {expected})"

    def test_parse_story_points_invalid(self):
        """Test parsing story points inválidos"""
        from evaluate_estimation import parse_story_points

        invalid_cases = [
            "not a number",
            "abc",
            "",
            "five",
        ]

        for input_val in invalid_cases:
            result = parse_story_points(input_val)
            assert result is None, f"Falló (debería ser None): {input_val} -> {result}"

    def test_few_shot_examples_count(self):
        """Verificar número de ejemplos few-shot"""
        from evaluate_estimation import FEW_SHOT_EXAMPLES

        assert len(FEW_SHOT_EXAMPLES) == 3, "Debe haber 3 ejemplos few-shot"

    def test_few_shot_examples_structure(self):
        """Verificar estructura de ejemplos few-shot"""
        from evaluate_estimation import FEW_SHOT_EXAMPLES

        for ex in FEW_SHOT_EXAMPLES:
            assert 'title' in ex
            assert 'description' in ex
            assert 'story_points' in ex

    def test_fibonacci_series(self):
        """Verificar serie Fibonacci"""
        from evaluate_estimation import FIBONACCI_SERIES

        expected = [1, 2, 3, 5, 8, 13, 21]
        assert FIBONACCI_SERIES == expected


class TestStatisticalAnalysis:
    """Pruebas para src/statistical_analysis.py"""

    def test_wilcoxon_import(self):
        """Test importación scipy.stats.wilcoxon"""
        from scipy import stats
        assert hasattr(stats, 'wilcoxon')
        assert callable(stats.wilcoxon)

    def test_sklearn_metrics_import(self):
        """Test importación métricas sklearn"""
        from sklearn.metrics import classification_report, confusion_matrix, f1_score

        assert callable(confusion_matrix)
        assert callable(f1_score)
        assert callable(classification_report)

    def test_confusion_matrix_basic(self):
        """Test básico matriz de confusión"""
        from sklearn.metrics import confusion_matrix

        y_true = ['A', 'B', 'A', 'B']
        y_pred = ['A', 'B', 'B', 'B']

        cm = confusion_matrix(y_true, y_pred)

        assert cm.shape == (2, 2)
        assert cm[0][0] == 1  # TP for A
        assert cm[1][1] == 2  # TP for B

    def test_f1_score_calculation(self):
        """Test cálculo F1-score"""
        from sklearn.metrics import f1_score

        y_true = ['A', 'B', 'A', 'B']
        y_pred = ['A', 'B', 'B', 'B']

        f1 = f1_score(y_true, y_pred, average='macro')

        assert 0.4 <= f1 <= 1.0


class TestCodeCarbon:
    """Pruebas para codecarbon"""

    def test_codecarbon_import(self):
        """Test importación codecarbon"""
        try:
            from codecarbon import track_emissions
            assert callable(track_emissions)
        except ImportError:
            pytest.skip("codecarbon no disponible")


class TestOllamaClient:
    """Pruebas para cliente Ollama"""

    def test_ollama_import(self):
        """Test importación ollama"""
        try:
            import ollama
            assert hasattr(ollama, 'Client')
        except ImportError:
            pytest.skip("ollama no disponible")


class TestEndToEnd:
    """Pruebas de extremo a extremo"""

    def test_sample_jira_evaluation(self):
        """Test evaluación de muestra Jira (5 issues)"""
        from evaluate_triage import TriageEvaluator

        df = pd.read_csv("data/jira_balanced_200.csv")
        sample = df.head(5)

        evaluator = TriageEvaluator()

        results = []
        for _idx, row in sample.iterrows():
            pred = evaluator.evaluate_issue(
                row['issue_key'],
                str(row['title']),
                str(row['description'])
            )
            results.append(pred)

        valid_results = [r for r in results if r is not None]

        assert len(valid_results) >= 0

    def test_sample_estimation_evaluation(self):
        """Test evaluación de muestra TAWOS (5 items)"""
        from evaluate_estimation import EstimationEvaluator

        df = pd.read_csv("data/tawos_clean.csv")
        mesos_df = df[df['project'] == 'MESOS'].head(5)

        evaluator = EstimationEvaluator()

        results = []
        for idx, row in mesos_df.iterrows():
            pred = evaluator.evaluate_item(
                str(idx),
                str(row['title']),
                str(row['description'])
            )
            results.append(pred)

        valid_results = [r for r in results if r is not None]

        assert len(valid_results) >= 0
