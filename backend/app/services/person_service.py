from sqlalchemy.orm import Session

from app.models.person import Person
from app.schemas.person import PersonCreate
from app.utils.cpf import only_digits, mask_cpf, is_valid_cpf


class PersonService:
    def __init__(self, db: Session):
        self.db = db

    def upsert_person(self, tenant_id, payload: PersonCreate) -> dict:
        cpf_digits = only_digits(payload.cpf)
        valid = is_valid_cpf(cpf_digits)

        person = (
            self.db.query(Person)
            .filter(
                Person.tenant_id == tenant_id,
                Person.cpf == cpf_digits,
            )
            .first()
        )

        if not person:
            person = Person(
                tenant_id=tenant_id,
                cpf=cpf_digits,
                cpf_masked=mask_cpf(cpf_digits),
                source="manual",
            )
            self.db.add(person)

        person.full_name = payload.full_name
        person.birth_date = payload.birth_date
        person.consent_reference = payload.consent_reference
        person.is_valid_cpf = valid
        person.validation_status = "valid" if valid else "invalid"

        self.db.commit()
        self.db.refresh(person)

        return self._build_response(person)

    def _build_response(self, person: Person) -> dict:
        checked_at = person.updated_at.isoformat() if person.updated_at else None

        if person.is_valid_cpf:
            validation_status_label = "CPF estruturalmente válido"
            risk_level = "baixo"
            commercial_summary = (
                "O CPF informado passou na validação estrutural oficial e pode seguir "
                "para continuidade cadastral, análise interna ou vínculo com uma operação."
            )
            recommended_action = (
                "Prosseguir com o cadastro e, se houver necessidade de score, restrições, "
                "protestos ou negativação, consultar bureau autorizado mediante base legal/consentimento."
            )
        else:
            validation_status_label = "CPF inválido pela validação estrutural"
            risk_level = "alto"
            commercial_summary = (
                "O CPF informado não passou na validação estrutural. Isso indica provável "
                "erro de digitação, documento incompleto ou número inconsistente."
            )
            recommended_action = (
                "Conferir o CPF com o titular antes de continuar qualquer cadastro, cobrança, "
                "crédito ou validação comercial."
            )

        lgpd_scope = (
            "Consulta estrutural registrada por tenant. Esta etapa não consulta score, "
            "restrições, protestos, negativação ou bases privadas. Para dados premium, "
            "é necessária integração autorizada com bureau e finalidade legítima."
        )

        return {
            "id": person.id,
            "cpf_masked": person.cpf_masked,
            "full_name": person.full_name,
            "birth_date": person.birth_date,
            "is_valid_cpf": person.is_valid_cpf,
            "validation_status": person.validation_status,
            "source": person.source,
            "consent_reference": person.consent_reference,
            "document_type": "CPF",
            "normalized_document": person.cpf_masked,
            "validation_status_label": validation_status_label,
            "risk_level": risk_level,
            "commercial_summary": commercial_summary,
            "recommended_action": recommended_action,
            "lgpd_scope": lgpd_scope,
            "bureau_required": True,
            "bureau_note": (
                "Score, restrições, protestos e negativação não são retornados nesta versão. "
                "Esses dados dependem de integração autorizada com Serasa/SPC/Boa Vista/Quod ou bureau equivalente."
            ),
            "checked_at": checked_at,
        }
