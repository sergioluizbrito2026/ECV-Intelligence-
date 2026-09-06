"""
ECV Intelligence V3
services/automation.py

Motor de automações da plataforma.

Responsabilidades:
- executar regras operacionais;
- identificar situações que exigem atenção;
- gerar alertas;
- registrar execuções;
- evitar execução duplicada;
- produzir insights;
- preparar integração futura com banco/API.

Arquitetura:

Dados
  ↓
Analytics
  ↓
Automation Engine
  ↓
Regras
  ↓
Ação
  ↓
Log / Insight / Alerta
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd


# ============================================================
# CONFIGURAÇÃO
# ============================================================

DEFAULT_COOLDOWN_MINUTES = 60


# ============================================================
# UTILITÁRIOS
# ============================================================

def _now():
    return datetime.now()


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize(value):
    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
    )


# ============================================================
# CLASSE PRINCIPAL
# ============================================================

class AutomationEngine:
    """
    Motor central de automações.

    Exemplo:

        engine = AutomationEngine()

        result = engine.evaluate(
            df,
            rules
        )
    """

    def __init__(
        self,
        cooldown_minutes=DEFAULT_COOLDOWN_MINUTES,
    ):

        self.cooldown_minutes = (
            cooldown_minutes
        )

        self.execution_log = []

    # ========================================================
    # AVALIAÇÃO
    # ========================================================

    def evaluate(
        self,
        df: pd.DataFrame,
        rules: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Avalia as regras contra os dados atuais.

        Retorna lista de ações que podem ser executadas.
        """

        if df is None or df.empty:

            return []

        if rules is None:

            rules = self.default_rules()

        triggered = []

        for rule in rules:

            try:

                result = self._evaluate_rule(
                    df,
                    rule,
                )

                if result:

                    triggered.append(
                        result
                    )

            except Exception as exc:

                triggered.append(
                    {
                        "rule_id": rule.get(
                            "id",
                            "unknown",
                        ),
                        "status": "error",
                        "message": str(exc),
                    }
                )

        return triggered

    # ========================================================
    # AVALIAÇÃO DE UMA REGRA
    # ========================================================

    def _evaluate_rule(
        self,
        df,
        rule,
    ):

        rule_id = rule.get(
            "id",
            "rule",
        )

        rule_type = _normalize(
            rule.get(
                "type",
                "",
            )
        )

        enabled = rule.get(
            "enabled",
            True,
        )

        if not enabled:

            return None

        # ----------------------------------------------------
        # REGRAS SUPORTADAS
        # ----------------------------------------------------

        if rule_type == "approval_rate":

            return self._rule_approval_rate(
                df,
                rule,
            )

        if rule_type == "high_rejection":

            return self._rule_high_rejection(
                df,
                rule,
            )

        if rule_type == "slow_inspection":

            return self._rule_slow_inspection(
                df,
                rule,
            )

        if rule_type == "data_quality":

            return self._rule_data_quality(
                df,
                rule,
            )

        if rule_type == "volume":

            return self._rule_volume(
                df,
                rule,
            )

        return {
            "rule_id": rule_id,
            "status": "unsupported",
            "message": (
                f"Tipo de regra não suportado: "
                f"{rule_type}"
            ),
        }

    # ========================================================
    # REGRA — TAXA DE APROVAÇÃO
    # ========================================================

    def _rule_approval_rate(
        self,
        df,
        rule,
    ):

        if "resultado" not in df.columns:

            return None

        resultado = (
            df["resultado"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        total = len(df)

        if total == 0:

            return None

        approved = int(
            (resultado == "aprovado")
            .sum()
        )

        rate = (
            approved
            / total
            * 100
        )

        threshold = _safe_float(
            rule.get(
                "threshold",
                80,
            )
        )

        # Dispara quando a aprovação fica abaixo
        # do limite configurado.

        if rate >= threshold:

            return None

        return self._build_trigger(
            rule,
            severity="high",
            title="Taxa de aprovação abaixo do esperado",
            message=(
                f"A taxa de aprovação atual é "
                f"{rate:.1f}%, abaixo do limite "
                f"de {threshold:.1f}%."
            ),
            data={
                "taxa_aprovacao": round(
                    rate,
                    2,
                ),
                "threshold": threshold,
                "total": total,
            },
        )

    # ========================================================
    # REGRA — REPROVAÇÃO
    # ========================================================

    def _rule_high_rejection(
        self,
        df,
        rule,
    ):

        if "resultado" not in df.columns:

            return None

        resultado = (
            df["resultado"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        total = len(df)

        if total == 0:

            return None

        rejected = int(
            (
                resultado
                == "reprovado"
            ).sum()
        )

        rate = (
            rejected
            / total
            * 100
        )

        threshold = _safe_float(
            rule.get(
                "threshold",
                20,
            )
        )

        if rate <= threshold:

            return None

        return self._build_trigger(
            rule,
            severity="high",
            title="Índice de reprovação elevado",
            message=(
                f"A taxa de reprovação está em "
                f"{rate:.1f}%, acima do limite de "
                f"{threshold:.1f}%."
            ),
            data={
                "taxa_reprovacao": round(
                    rate,
                    2,
                ),
                "threshold": threshold,
                "reprovadas": rejected,
                "total": total,
            },
        )

    # ========================================================
    # REGRA — TEMPO DE VISTORIA
    # ========================================================

    def _rule_slow_inspection(
        self,
        df,
        rule,
    ):

        if "tempo_minutos" not in df.columns:

            return None

        tempo = pd.to_numeric(
            df["tempo_minutos"],
            errors="coerce",
        )

        if not tempo.notna().any():

            return None

        average = float(
            tempo.mean()
        )

        threshold = _safe_float(
            rule.get(
                "threshold",
                60,
            )
        )

        if average <= threshold:

            return None

        return self._build_trigger(
            rule,
            severity="medium",
            title="Tempo médio elevado",
            message=(
                f"O tempo médio das vistorias "
                f"está em {average:.1f} minutos, "
                f"acima do limite de "
                f"{threshold:.1f} minutos."
            ),
            data={
                "tempo_medio": round(
                    average,
                    2,
                ),
                "threshold": threshold,
            },
        )

    # ========================================================
    # REGRA — QUALIDADE
    # ========================================================

    def _rule_data_quality(
        self,
        df,
        rule,
    ):

        from services.analytics import (
            get_quality_report,
        )

        report = get_quality_report(
            df
        )

        score = _safe_float(
            report.get(
                "score",
                100,
            )
        )

        threshold = _safe_float(
            rule.get(
                "threshold",
                85,
            )
        )

        if score >= threshold:

            return None

        return self._build_trigger(
            rule,
            severity="high",
            title="Qualidade dos dados abaixo do esperado",
            message=(
                f"O score de qualidade está em "
                f"{score:.1f}%, abaixo do limite "
                f"de {threshold:.1f}%."
            ),
            data=report,
        )

    # ========================================================
    # REGRA — VOLUME
    # ========================================================

    def _rule_volume(
        self,
        df,
        rule,
    ):

        total = len(df)

        threshold = _safe_int(
            rule.get(
                "threshold",
                100,
            )
        )

        direction = _normalize(
            rule.get(
                "direction",
                "above",
            )
        )

        triggered = False

        if direction in (
            "above",
            "maior",
            "acima",
        ):

            triggered = (
                total > threshold
            )

        elif direction in (
            "below",
            "menor",
            "abaixo",
        ):

            triggered = (
                total < threshold
            )

        if not triggered:

            return None

        return self._build_trigger(
            rule,
            severity="medium",
            title="Volume de vistorias atingiu condição configurada",
            message=(
                f"O volume atual é de "
                f"{total} vistorias. "
                f"Condição configurada: "
                f"{direction} {threshold}."
            ),
            data={
                "total": total,
                "threshold": threshold,
                "direction": direction,
            },
        )

    # ========================================================
    # CONSTRUÇÃO DO EVENTO
    # ========================================================

    def _build_trigger(
        self,
        rule,
        severity,
        title,
        message,
        data,
    ):

        return {
            "rule_id": rule.get(
                "id",
                "rule",
            ),
            "rule_name": rule.get(
                "name",
                "Automação",
            ),
            "action": rule.get(
                "action",
                "alert",
            ),
            "severity": severity,
            "title": title,
            "message": message,
            "data": data,
            "timestamp": _now().isoformat(),
            "status": "triggered",
        }

    # ========================================================
    # EXECUÇÃO
    # ========================================================

    def execute(
        self,
        trigger,
        force=False,
    ):
        """
        Executa uma automação já disparada.

        Atualmente registra a execução em memória.
        A integração persistente com SQLite/API pode ser
        adicionada posteriormente.
        """

        if not trigger:

            return {
                "status": "ignored",
                "message": "Nenhum evento recebido.",
            }

        rule_id = trigger.get(
            "rule_id",
            "unknown",
        )

        if (
            not force
            and self._in_cooldown(rule_id)
        ):

            return {
                "status": "cooldown",
                "rule_id": rule_id,
                "message": (
                    "Automação ignorada porque "
                    "está dentro do período de cooldown."
                ),
            }

        action = _normalize(
            trigger.get(
                "action",
                "alert",
            )
        )

        result = self._execute_action(
            action,
            trigger,
        )

        execution = {
            "rule_id": rule_id,
            "action": action,
            "timestamp": _now().isoformat(),
            "result": result,
        }

        self.execution_log.append(
            execution
        )

        return {
            "status": "executed",
            "execution": execution,
        }

    # ========================================================
    # AÇÕES
    # ========================================================

    def _execute_action(
        self,
        action,
        trigger,
    ):

        if action == "alert":

            return {
                "type": "alert",
                "title": trigger.get(
                    "title",
                    "Alerta",
                ),
                "message": trigger.get(
                    "message",
                    "",
                ),
            }

        if action == "insight":

            return {
                "type": "insight",
                "title": trigger.get(
                    "title",
                    "Insight",
                ),
                "message": trigger.get(
                    "message",
                    "",
                ),
                "data": trigger.get(
                    "data",
                    {},
                ),
            }

        if action == "log":

            return {
                "type": "log",
                "message": trigger.get(
                    "message",
                    "",
                ),
            }

        if action == "notify":

            return {
                "type": "notification",
                "message": trigger.get(
                    "message",
                    "",
                ),
            }

        return {
            "type": "unknown",
            "message": (
                f"Ação '{action}' "
                "não possui executor configurado."
            ),
        }

    # ========================================================
    # COOLDOWN
    # ========================================================

    def _in_cooldown(
        self,
        rule_id,
    ):

        if not self.execution_log:

            return False

        limit = (
            _now()
            - timedelta(
                minutes=self.cooldown_minutes
            )
        )

        for execution in reversed(
            self.execution_log
        ):

            if execution.get(
                "rule_id"
            ) != rule_id:

                continue

            try:

                timestamp = datetime.fromisoformat(
                    execution[
                        "timestamp"
                    ]
                )

            except Exception:

                continue

            if timestamp >= limit:

                return True

            break

        return False

    # ========================================================
    # LOG
    # ========================================================

    def get_execution_log(self):

        return list(
            self.execution_log
        )

    # ========================================================
    # REGRAS PADRÃO
    # ========================================================

    @staticmethod
    def default_rules():

        return [
            {
                "id": "approval_rate",
                "name": "Taxa de aprovação",
                "type": "approval_rate",
                "threshold": 80,
                "action": "alert",
                "enabled": True,
            },
            {
                "id": "high_rejection",
                "name": "Alta reprovação",
                "type": "high_rejection",
                "threshold": 20,
                "action": "alert",
                "enabled": True,
            },
            {
                "id": "slow_inspection",
                "name": "Tempo elevado",
                "type": "slow_inspection",
                "threshold": 60,
                "action": "insight",
                "enabled": True,
            },
            {
                "id": "data_quality",
                "name": "Qualidade dos dados",
                "type": "data_quality",
                "threshold": 85,
                "action": "alert",
                "enabled": True,
            },
        ]


# ============================================================
# FUNÇÕES DE ALTO NÍVEL
# ============================================================

def evaluate_automations(
    df,
    rules=None,
):
    """
    Atalho para avaliação das automações.
    """

    engine = AutomationEngine()

    return engine.evaluate(
        df,
        rules,
    )


def run_automations(
    df,
    rules=None,
):
    """
    Avalia e executa as automações disparadas.
    """

    engine = AutomationEngine()

    triggers = engine.evaluate(
        df,
        rules,
    )

    results = []

    for trigger in triggers:

        if trigger.get(
            "status"
        ) != "triggered":

            results.append(
                trigger
            )

            continue

        results.append(
            engine.execute(
                trigger
            )
        )

    return results


def get_automation_summary(
    df,
    rules=None,
):
    """
    Retorna um resumo executivo das automações.
    """

    engine = AutomationEngine()

    triggers = engine.evaluate(
        df,
        rules,
    )

    active = [
        item
        for item in triggers
        if item.get(
            "status"
        ) == "triggered"
    ]

    high = [
        item
        for item in active
        if item.get(
            "severity"
        ) == "high"
    ]

    medium = [
        item
        for item in active
        if item.get(
            "severity"
        ) == "medium"
    ]

    return {
        "total_regras": len(
            rules
            if rules is not None
            else engine.default_rules()
        ),
        "disparadas": len(
            active
        ),
        "criticas": len(
            high
        ),
        "atencao": len(
            medium
        ),
        "eventos": active,
    }
