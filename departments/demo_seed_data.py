DEMO_CREDENTIALS = {
    "super_admin": {
        "username": "superadmin",
        "password": "DemoSuperAdmin123!",
        "email": "superadmin.demo@norsu.edu.ph",
        "full_name": "University Super Admin",
    },
    "department_admin_password": "DemoDeptAdmin123!",
}


DEMO_SCHOOL_INFO = {
    "college_name": "Negros Oriental State University",
    "mission": (
        "Negros Oriental State University advances quality instruction, relevant research, "
        "responsive extension, and sustainable innovation in service of learners and communities."
    ),
    "vision": (
        "A leading state university in the region recognized for academic excellence, ethical leadership, "
        "and transformative community engagement."
    ),
    "history": (
        "Negros Oriental State University has continued to expand its educational reach through accessible "
        "programs, strong local partnerships, and a commitment to public service. Its colleges and academic "
        "units reflect a growing tradition of professional preparation, community relevance, and regional impact."
    ),
}


DEMO_DEPARTMENTS = [
    {
        "code": "CAS",
        "name": "College of Arts and Sciences",
        "description": "Offers foundational and emerging disciplines in the sciences, humanities, and computing.",
        "theme_color": "#0f6b4f",
        "theme_color_secondary": "#2563eb",
        "admin": {
            "username": "cas_admin",
            "email": "cas.admin.demo@norsu.edu.ph",
            "full_name": "CAS Department Admin",
        },
        "programs": [
            {
                "program_code": "BSINT",
                "program_name": "Bachelor of Science in Information Technology",
                "description": "Prepares students in software development, systems administration, and digital solutions for industry and public service.",
            },
            {
                "program_code": "BS COM TECH",
                "program_name": "Bachelor of Science in Computer Science",
                "description": "Builds strong foundations in algorithms, programming, software engineering, and computational problem solving.",
            },
        ],
        "instructors": [
            "Dr. Amelia V. Ramos",
            "Prof. Jeffrey T. Mendoza",
            "Prof. Lea Marie S. Atienza",
        ],
        "announcements": [
            {
                "title": "CAS Opens Student Research Proposal Clinic",
                "content": "The College of Arts and Sciences will conduct a week-long proposal clinic for graduating students to strengthen research design, writing, and oral presentation readiness.",
            },
            {
                "title": "Laboratory Schedule for Computing Courses Updated",
                "content": "Computer laboratory sections for the current term have been adjusted to improve equipment access and reduce overlapping schedules.",
            },
        ],
        "news": [
            {
                "title": "CAS Team Recognized in Regional Innovation Challenge",
                "content": "A student team from the college received recognition for a community-based information system concept presented during the regional innovation showcase.",
            },
            {
                "title": "Faculty Members Complete Outcomes-Based Education Workshop",
                "content": "Faculty members from the college completed a capability-building workshop focused on assessment alignment and student-centered course design.",
            },
        ],
        "events": [
            {
                "title": "CAS Research Colloquium",
                "description": "An academic forum featuring undergraduate research presentations from science and computing students.",
                "event_date": "2026-05-12 09:00",
                "location": "University Audio-Visual Hall",
            },
            {
                "title": "Programming Skills Bootcamp",
                "description": "A two-day enhancement session for students preparing for internships and capstone development.",
                "event_date": "2026-06-03 08:30",
                "location": "CAS Computer Laboratory",
            },
        ],
        "alumni": [
            {
                "full_name": "Marvin T. Abella",
                "batch_year": 2021,
                "course_program": "BSINT - Bachelor of Science in Information Technology",
                "email": "marvin.abella.demo@example.com",
                "contact_number": "09171230001",
                "address": "Dumaguete City, Negros Oriental",
                "employment_status": "Employed",
                "company_name": "Southeast Tech Solutions",
                "job_title": "Junior Software Developer",
                "is_public": True,
            },
            {
                "full_name": "Angela P. Vibar",
                "batch_year": 2020,
                "course_program": "BS COM TECH - Bachelor of Science in Computer Science",
                "email": "angela.vibar.demo@example.com",
                "contact_number": "09171230002",
                "address": "Valencia, Negros Oriental",
                "employment_status": "Employed",
                "company_name": "DataBridge Analytics",
                "job_title": "QA Analyst",
                "is_public": False,
            },
        ],
    },
    {
        "code": "CTED",
        "name": "College of Teacher Education",
        "description": "Develops future educators equipped for classroom leadership, pedagogy, and community-responsive teaching.",
        "theme_color": "#1f6f8b",
        "theme_color_secondary": "#f59e0b",
        "admin": {
            "username": "cted_admin",
            "email": "cted.admin.demo@norsu.edu.ph",
            "full_name": "CTED Department Admin",
        },
        "programs": [
            {
                "program_code": "BSED-MATH",
                "program_name": "Bachelor of Secondary Education Major in Mathematics",
                "description": "Trains future mathematics teachers in content mastery, instructional strategies, and assessment practice.",
            },
            {
                "program_code": "BSED-ENGLISH",
                "program_name": "Bachelor of Secondary Education Major in English",
                "description": "Builds competence in language instruction, literature, communication, and curriculum design.",
            },
            {
                "program_code": "BSED-SCIENCE",
                "program_name": "Bachelor of Secondary Education Major in Science",
                "description": "Prepares science educators through inquiry-based teaching and practical laboratory integration.",
            },
            {
                "program_code": "BEED-GC",
                "program_name": "Bachelor of Elementary Education General Curriculum",
                "description": "Provides broad elementary education preparation for learner development and classroom management.",
            },
        ],
        "instructors": [
            "Dr. Roselyn A. Lim",
            "Prof. Benedict S. Alcoran",
            "Prof. Hazel T. Sarmiento",
        ],
        "announcements": [
            {
                "title": "CTED Practice Teaching Orientation Set for Juniors",
                "content": "An orientation on field study and practice teaching requirements will be held for junior education students preparing for off-campus placements.",
            },
            {
                "title": "Teaching Demonstration Rubrics Released",
                "content": "Updated teaching demonstration criteria are now available to help students prepare for observation and final evaluation.",
            },
        ],
        "news": [
            {
                "title": "CTED Graduates Post Strong Licensure Review Performance",
                "content": "Recent graduates from the college participated in an internal review program that showed encouraging results in mock board assessments.",
            },
            {
                "title": "Education Faculty Lead Reading Outreach in Partner Schools",
                "content": "Faculty and student volunteers conducted literacy support sessions with selected elementary learners in nearby communities.",
            },
        ],
        "events": [
            {
                "title": "Teaching Innovations Forum",
                "description": "A forum on inclusive teaching methods, classroom technology, and formative assessment strategies.",
                "event_date": "2026-05-21 13:30",
                "location": "CTED Lecture Room 2",
            },
            {
                "title": "Campus Reading Month Launch",
                "description": "Opening activity for reading month featuring student storytellers, literacy booths, and teaching resource exhibits.",
                "event_date": "2026-06-10 08:00",
                "location": "University Covered Court",
            },
        ],
        "alumni": [
            {
                "full_name": "Janine M. Teves",
                "batch_year": 2019,
                "course_program": "BSED-ENGLISH - Bachelor of Secondary Education Major in English",
                "email": "janine.teves.demo@example.com",
                "contact_number": "09171230003",
                "address": "Sibulan, Negros Oriental",
                "employment_status": "Employed",
                "company_name": "DepEd Negros Oriental",
                "job_title": "Public School Teacher",
                "is_public": True,
            },
            {
                "full_name": "Carlo P. Mercader",
                "batch_year": 2022,
                "course_program": "BEED-GC - Bachelor of Elementary Education General Curriculum",
                "email": "carlo.mercader.demo@example.com",
                "contact_number": "09171230004",
                "address": "Bais City, Negros Oriental",
                "employment_status": "Seeking Employment",
                "company_name": "",
                "job_title": "",
                "is_public": False,
            },
        ],
    },
    {
        "code": "CCJE",
        "name": "College of Criminal Justice Education",
        "description": "Provides academic and professional preparation for criminology, public safety, and justice-oriented service.",
        "theme_color": "#6b1f2a",
        "theme_color_secondary": "#d97706",
        "admin": {
            "username": "ccje_admin",
            "email": "ccje.admin.demo@norsu.edu.ph",
            "full_name": "CCJE Department Admin",
        },
        "programs": [
            {
                "program_code": "BS CRIM",
                "program_name": "Bachelor of Science in Criminology",
                "description": "Equips students with competencies in criminal justice systems, law enforcement practice, and community safety.",
            },
        ],
        "instructors": [
            "Dr. Renato M. Ligan",
            "Prof. Joy Ann D. Catamco",
            "Prof. Noel R. Batingal",
        ],
        "announcements": [
            {
                "title": "CCJE Uniform and Formation Guidelines Issued",
                "content": "Students are advised to review the updated uniform standards and formation procedures for official college activities.",
            },
            {
                "title": "Simulation Lab Schedule Posted",
                "content": "The practicum and simulation laboratory schedule for criminology majors is now available at the department office and online bulletin.",
            },
        ],
        "news": [
            {
                "title": "CCJE Hosts Campus Safety Awareness Seminar",
                "content": "The college organized a campus safety seminar highlighting emergency preparedness, student responsibility, and coordinated response procedures.",
            },
            {
                "title": "Criminology Students Join Community Crime Prevention Campaign",
                "content": "Students participated in a local campaign focused on awareness-building and neighborhood coordination for public safety.",
            },
        ],
        "events": [
            {
                "title": "Criminalistics Skills Demonstration",
                "description": "Hands-on demonstration of fingerprint lifting, evidence handling, and crime scene documentation techniques.",
                "event_date": "2026-05-28 10:00",
                "location": "CCJE Simulation Laboratory",
            },
            {
                "title": "Justice and Ethics Lecture Series",
                "description": "Guest lecture series featuring practitioners in policing, prosecution, and forensic investigation.",
                "event_date": "2026-06-14 14:00",
                "location": "University Mini Theater",
            },
        ],
        "alumni": [
            {
                "full_name": "Jerome F. Matias",
                "batch_year": 2018,
                "course_program": "BS CRIM - Bachelor of Science in Criminology",
                "email": "jerome.matias.demo@example.com",
                "contact_number": "09171230005",
                "address": "Tanjay City, Negros Oriental",
                "employment_status": "Employed",
                "company_name": "Local Government Unit",
                "job_title": "Public Safety Officer",
                "is_public": True,
            },
            {
                "full_name": "Diana C. Villanueva",
                "batch_year": 2021,
                "course_program": "BS CRIM - Bachelor of Science in Criminology",
                "email": "diana.villanueva.demo@example.com",
                "contact_number": "09171230006",
                "address": "Amlan, Negros Oriental",
                "employment_status": "Employed",
                "company_name": "Private Security Agency",
                "job_title": "Operations Staff",
                "is_public": False,
            },
        ],
    },
    {
        "code": "CBA",
        "name": "College of Business Administration",
        "description": "Focuses on business, accountancy, office administration, and service-oriented management education.",
        "theme_color": "#9a6b12",
        "theme_color_secondary": "#facc15",
        "admin": {
            "username": "cba_admin",
            "email": "cba.admin.demo@norsu.edu.ph",
            "full_name": "CBA Department Admin",
        },
        "programs": [
            {
                "program_code": "BSA",
                "program_name": "Bachelor of Science in Accountancy",
                "description": "Builds strong foundations in financial reporting, taxation, auditing, and professional ethics.",
            },
            {
                "program_code": "BSOA",
                "program_name": "Bachelor of Science in Office Administration",
                "description": "Develops administrative, communication, and records management skills for professional office environments.",
            },
            {
                "program_code": "BSHM",
                "program_name": "Bachelor of Science in Hospitality Management",
                "description": "Prepares students for hospitality operations, service leadership, and tourism-related enterprise management.",
            },
        ],
        "instructors": [
            "Dr. Eleanor G. Gica",
            "Prof. Samuel R. Mapalo",
            "Prof. Mae Cristine Y. Berja",
        ],
        "announcements": [
            {
                "title": "CBA Internship Briefing Scheduled",
                "content": "All internship-bound students are required to attend the upcoming briefing on placement procedures, requirements, and workplace expectations.",
            },
            {
                "title": "Hospitality Laboratory Uniform Check This Week",
                "content": "Hospitality management students are advised to comply with laboratory attire requirements before scheduled kitchen and front-office sessions.",
            },
        ],
        "news": [
            {
                "title": "CBA Students Present Business Pitch Concepts",
                "content": "Students showcased startup concepts that focused on local enterprise, service innovation, and sustainable business planning.",
            },
            {
                "title": "Accountancy Faculty Conduct Tax Updates Seminar",
                "content": "Faculty members facilitated a seminar on recent tax policy updates and their classroom integration for accountancy students.",
            },
        ],
        "events": [
            {
                "title": "Entrepreneurship Week Opening Program",
                "description": "A week-long celebration featuring student exhibits, product booths, and entrepreneurship mentoring sessions.",
                "event_date": "2026-05-19 09:30",
                "location": "CBA Activity Area",
            },
            {
                "title": "Hospitality Service Excellence Workshop",
                "description": "Training activity focused on guest relations, event coordination, and service standards.",
                "event_date": "2026-06-07 13:00",
                "location": "Hospitality Management Laboratory",
            },
        ],
        "alumni": [
            {
                "full_name": "Nicole R. Dela Pena",
                "batch_year": 2020,
                "course_program": "BSHM - Bachelor of Science in Hospitality Management",
                "email": "nicole.delapena.demo@example.com",
                "contact_number": "09171230007",
                "address": "Dauin, Negros Oriental",
                "employment_status": "Employed",
                "company_name": "Oceanfront Suites",
                "job_title": "Guest Relations Officer",
                "is_public": True,
            },
            {
                "full_name": "Paolo V. Escano",
                "batch_year": 2019,
                "course_program": "BSA - Bachelor of Science in Accountancy",
                "email": "paolo.escano.demo@example.com",
                "contact_number": "09171230008",
                "address": "Bayawan City, Negros Oriental",
                "employment_status": "Employed",
                "company_name": "NOVA Accounting Partners",
                "job_title": "Audit Associate",
                "is_public": False,
            },
        ],
    },
    {
        "code": "CIT",
        "name": "College of Industrial Technology",
        "description": "Offers applied technology programs that support technical competence, industry readiness, and innovation.",
        "theme_color": "#4b5563",
        "theme_color_secondary": "#0ea5e9",
        "admin": {
            "username": "cit_admin",
            "email": "cit.admin.demo@norsu.edu.ph",
            "full_name": "CIT Department Admin",
        },
        "programs": [
            {
                "program_code": "BSIT",
                "program_name": "Bachelor of Science in Information Technology",
                "description": "Develops digital systems, network support, and practical computing solutions aligned with applied industry needs.",
            },
            {
                "program_code": "BSAT",
                "program_name": "Bachelor of Science in Automotive Technology",
                "description": "Provides technical preparation in vehicle systems, diagnostics, maintenance, and workshop operations.",
            },
            {
                "program_code": "BSET",
                "program_name": "Bachelor of Science in Electrical Technology",
                "description": "Builds competencies in electrical systems, industrial safety, and applied installation practices.",
            },
            {
                "program_code": "BSCT",
                "program_name": "Bachelor of Science in Computer Technology",
                "description": "Focuses on hardware servicing, systems support, and technical maintenance for computing environments.",
            },
        ],
        "instructors": [
            "Dr. Roberto L. Catalan",
            "Prof. Nina K. Albao",
            "Prof. Jeffrey P. Mison",
        ],
        "announcements": [
            {
                "title": "CIT Workshop Safety Orientation Required",
                "content": "Students with scheduled laboratory and shop courses must attend the semester safety orientation before equipment use.",
            },
            {
                "title": "Tool Inventory and Borrowing Rules Updated",
                "content": "The college released updated guidelines for tool issuance, accountability, and laboratory checkout procedures.",
            },
        ],
        "news": [
            {
                "title": "CIT Students Showcase Applied Technology Projects",
                "content": "Student groups presented prototypes and technical solutions designed for community and small-industry applications.",
            },
            {
                "title": "Faculty Strengthen Industry Linkages for Practicum Sites",
                "content": "The college expanded industry coordination efforts to provide more relevant practicum exposure for graduating students.",
            },
        ],
        "events": [
            {
                "title": "Technology Skills Expo",
                "description": "Exhibit of student-built systems, machine applications, and technical demonstrations from multiple CIT programs.",
                "event_date": "2026-05-30 08:30",
                "location": "CIT Workshop Complex",
            },
            {
                "title": "Industrial Safety and Maintenance Seminar",
                "description": "A seminar on workplace safety standards, preventive maintenance, and shop management practices.",
                "event_date": "2026-06-18 13:30",
                "location": "CIT Seminar Hall",
            },
        ],
        "alumni": [
            {
                "full_name": "Rico S. Bagarinao",
                "batch_year": 2021,
                "course_program": "BSCT - Bachelor of Science in Computer Technology",
                "email": "rico.bagarinao.demo@example.com",
                "contact_number": "09171230009",
                "address": "Bacong, Negros Oriental",
                "employment_status": "Employed",
                "company_name": "Axis Technical Services",
                "job_title": "Technical Support Specialist",
                "is_public": True,
            },
            {
                "full_name": "Mark Anthony P. Jereza",
                "batch_year": 2020,
                "course_program": "BSAT - Bachelor of Science in Automotive Technology",
                "email": "mark.jereza.demo@example.com",
                "contact_number": "09171230010",
                "address": "Guihulngan City, Negros Oriental",
                "employment_status": "Employed",
                "company_name": "Prime AutoWorks",
                "job_title": "Service Technician",
                "is_public": False,
            },
        ],
    },
    {
        "code": "CAF",
        "name": "College of Agriculture and Forestry",
        "description": "Promotes sustainable agriculture, resource management, and science-based environmental stewardship.",
        "theme_color": "#3f7d20",
        "theme_color_secondary": "#84cc16",
        "admin": {
            "username": "caf_admin",
            "email": "caf.admin.demo@norsu.edu.ph",
            "full_name": "CAF Department Admin",
        },
        "programs": [
            {
                "program_code": "BSA",
                "program_name": "Bachelor of Science in Agriculture",
                "description": "Prepares students in crop production, farm management, extension practice, and sustainable agricultural systems.",
            },
            {
                "program_code": "BS ANSCI",
                "program_name": "Bachelor of Science in Animal Science",
                "description": "Builds expertise in animal production, nutrition, farm operations, and livestock care.",
            },
            {
                "program_code": "BSF",
                "program_name": "Bachelor of Science in Forestry",
                "description": "Develops knowledge in environmental conservation, forest resource management, and field-based stewardship.",
            },
        ],
        "instructors": [
            "Dr. Liza M. Villasis",
            "Prof. Arturo D. Cabrillos",
            "Prof. Felina O. Serino",
        ],
        "announcements": [
            {
                "title": "CAF Field Practicum Deployment Schedule Released",
                "content": "Students assigned to farm and forestry practicum areas may now review deployment schedules and site requirements.",
            },
            {
                "title": "Nursery Maintenance Volunteer Program Open",
                "content": "The college invites students to participate in nursery upkeep, seedling monitoring, and campus greening support activities.",
            },
        ],
        "news": [
            {
                "title": "CAF Launches Sustainable Farming Demonstration Plot",
                "content": "The college opened a demonstration plot to highlight soil health, crop planning, and practical sustainability strategies.",
            },
            {
                "title": "Forestry Students Join Watershed Conservation Activity",
                "content": "Students participated in a conservation initiative focused on environmental awareness and resource stewardship.",
            },
        ],
        "events": [
            {
                "title": "Agri-Technology Field Day",
                "description": "Field-based learning activity featuring crop demonstrations, equipment showcases, and farm management talks.",
                "event_date": "2026-05-24 07:30",
                "location": "CAF Demonstration Farm",
            },
            {
                "title": "Tree Growing and Ecosystem Awareness Campaign",
                "description": "Environmental action day with student volunteers, partner agencies, and community participants.",
                "event_date": "2026-06-20 06:30",
                "location": "University Reforestation Site",
            },
        ],
        "alumni": [
            {
                "full_name": "Elmer J. Beldia",
                "batch_year": 2018,
                "course_program": "BSA - Bachelor of Science in Agriculture",
                "email": "elmer.beldia.demo@example.com",
                "contact_number": "09171230011",
                "address": "Canlaon City, Negros Oriental",
                "employment_status": "Employed",
                "company_name": "Greenfields Agri Cooperative",
                "job_title": "Farm Operations Supervisor",
                "is_public": True,
            },
            {
                "full_name": "Sheena Mae R. Tablate",
                "batch_year": 2022,
                "course_program": "BSF - Bachelor of Science in Forestry",
                "email": "sheena.tablate.demo@example.com",
                "contact_number": "09171230012",
                "address": "Mabinay, Negros Oriental",
                "employment_status": "Further Studies",
                "company_name": "",
                "job_title": "",
                "is_public": False,
            },
        ],
    },
]
