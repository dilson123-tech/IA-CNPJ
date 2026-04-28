from sqlalchemy.orm import Session

from app.models.person import Person
from app.schemas.person import PersonCreate
from app.utils.cpf import only_digits, mask_cpf, is_valid_cpf


class PersonService:
    def __init__(self, db: Session):
        self.db = db

    def upsert_person(self, tenant_id, payload: PersonCreate) -> Person:
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

        return person
