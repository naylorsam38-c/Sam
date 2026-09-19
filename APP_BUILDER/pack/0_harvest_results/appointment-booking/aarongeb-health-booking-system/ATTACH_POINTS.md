# Attach Points

Application: aaronGeb/health_booking_system
Repository: aaronGeb/health_booking_system
Commit: 
Framework: django
Datastore: postgresql

## Events
| Name | Source | Symbol | Payload | Implementation | Evidence |
|------|--------|--------|---------|----------------|----------|

## Slots
| Name | Source | Rendering Context | Implementation | Evidence |
|------|--------|-------------------|----------------|----------|

## Data
| Name | Model/Table/Entity | Operations | Fields/Interface | Evidence |
|------|--------------------|------------|------------------|----------|
| doctors.Doctor | Doctor | READ | user, specialization, license_number, years_of_experience, qualification, hospital_affiliation, consultation_fee, biography, profile_picture, status, is_available, created_at, updated_at | doctors/models.py:22, accounts/models.py (referenced) |

## Extension System

(not recorded on the form)

## Adapter Requirements

None. Every attach point above is native to the source.
