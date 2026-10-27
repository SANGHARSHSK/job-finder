from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import EmployerProfile
from companies.models import Company
from jobs.models import Job


DEMO_JOBS = [
    (
        "Northstar Analytics",
        "Data Analyst",
        "Bengaluru, India",
        Job.EmploymentType.FULL_TIME,
        Job.ExperienceLevel.ENTRY,
        800000,
        1200000,
        "Analyze product and customer datasets, build clear dashboards, and share findings with product and operations teams.",
        "SQL, spreadsheets, data visualization, and clear written communication.",
    ),
    (
        "Mango Tree Labs",
        "Frontend Engineer",
        "Remote (India)",
        Job.EmploymentType.FULL_TIME,
        Job.ExperienceLevel.MID,
        1800000,
        2600000,
        "Build accessible, responsive interfaces for a growing SaaS product. Work with design and backend teams to ship customer-facing features.",
        "3+ years with JavaScript or TypeScript and React; HTML, CSS, accessibility, and API integration.",
    ),
    (
        "Copper Cloud",
        "Customer Support Associate",
        "Pune, India",
        Job.EmploymentType.FULL_TIME,
        Job.ExperienceLevel.ENTRY,
        500000,
        750000,
        "Help customers use our cloud bookkeeping platform through email and chat. Document recurring issues and partner with product on improvements.",
        "Strong written communication, comfort with web apps, and willingness to work rotating shifts.",
    ),
    (
        "Greenfield Robotics",
        "Embedded Systems Intern",
        "Hyderabad, India",
        Job.EmploymentType.INTERNSHIP,
        Job.ExperienceLevel.ENTRY,
        300000,
        420000,
        "Join the robotics team for a six-month internship building and testing firmware for sensor modules and mobile robots.",
        "Pursuing electrical engineering, computer science, or a related degree; C or C++ fundamentals.",
    ),
    (
        "Juniper Health",
        "Product Designer",
        "Remote (India)",
        Job.EmploymentType.FULL_TIME,
        Job.ExperienceLevel.SENIOR,
        2200000,
        3200000,
        "Lead research and interaction design for patient and clinician workflows. Develop prototypes, test them with users, and work closely with engineering through launch.",
        "5+ years in product design; strong Figma skills, research practice, and a portfolio of shipped work.",
    ),
    (
        "Harbor & Pine",
        "Operations Coordinator",
        "Mumbai, India",
        Job.EmploymentType.FULL_TIME,
        Job.ExperienceLevel.MID,
        700000,
        1000000,
        "Coordinate vendor schedules, maintain operational records, and improve processes across our growing retail network.",
        "2+ years in operations or logistics; strong spreadsheet skills and attention to detail.",
    ),
]


class Command(BaseCommand):
    help = "Create clearly labeled fictional job listings for a portfolio demo."

    def handle(self, *args, **options):
        User = get_user_model()
        created_jobs = 0

        for index, row in enumerate(DEMO_JOBS, start=1):
            (
                company_name,
                title,
                location,
                employment_type,
                experience_level,
                salary_min,
                salary_max,
                description,
                requirements,
            ) = row
            username = f"demo_employer_{index}"
            user, created_user = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "role": User.Role.EMPLOYER,
                },
            )
            if created_user:
                user.set_unusable_password()
                user.save(update_fields=["password"])

            profile, _ = EmployerProfile.objects.get_or_create(user=user)
            company, _ = Company.objects.get_or_create(
                owner=profile,
                defaults={
                    "name": f"Demo · {company_name}",
                    "description": (
                        "Fictional sample employer created for demonstration only. "
                        "This is not a real company or job opening."
                    ),
                    "website": "https://example.com",
                    "location": location,
                    "industry": "Technology (sample data)",
                },
            )
            _, created_job = Job.objects.get_or_create(
                company=company,
                title=f"{title} (Demo)",
                defaults={
                    "description": description,
                    "requirements": requirements,
                    "location": location,
                    "employment_type": employment_type,
                    "experience_level": experience_level,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "status": Job.Status.OPEN,
                },
            )
            created_jobs += int(created_job)

        self.stdout.write(
            self.style.SUCCESS(f"Created {created_jobs} demo jobs; demo data is clearly labeled.")
        )
