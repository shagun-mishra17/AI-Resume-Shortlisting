
import streamlit as st
import re
import io
import csv

from pypdf import PdfReader
from docx import Document


st.set_page_config(
    page_title="AI Resume Shortlisting",
    page_icon="📄",
    layout="wide"
)


# ---------------- HASH MAP ----------------

class HashMap:
    def __init__(self, size=101):
        self.size = size
        self.table = [[] for _ in range(size)]

    def hash_function(self, key):
        return sum(ord(c) for c in key) % self.size

    def put(self, key, value):
        index = self.hash_function(key)
        for item in self.table[index]:
            if item[0] == key:
                item[1] = value
                return
        self.table[index].append([key, value])

    def get(self, key):
        index = self.hash_function(key)
        for item in self.table[index]:
            if item[0] == key:
                return item[1]
        return None

    def keys(self):
        return [
            item[0]
            for bucket in self.table
            for item in bucket
        ]


# ---------------- MAX HEAP ----------------

class MaxHeap:
    def __init__(self):
        self.heap = []

    def push(self, item):
        self.heap.append(item)
        i = len(self.heap) - 1

        while i > 0:
            parent = (i - 1) // 2
            if self.heap[parent][0] >= self.heap[i][0]:
                break
            self.heap[parent], self.heap[i] = (
                self.heap[i], self.heap[parent]
            )
            i = parent

    def pop(self):
        if not self.heap:
            return None

        if len(self.heap) == 1:
            return self.heap.pop()

        maximum = self.heap[0]
        self.heap[0] = self.heap.pop()
        i = 0

        while True:
            left = 2 * i + 1
            right = 2 * i + 2
            largest = i

            if left < len(self.heap) and self.heap[left][0] > self.heap[largest][0]:
                largest = left

            if right < len(self.heap) and self.heap[right][0] > self.heap[largest][0]:
                largest = right

            if largest == i:
                break

            self.heap[i], self.heap[largest] = (
                self.heap[largest], self.heap[i]
            )
            i = largest

        return maximum

    def is_empty(self):
        return len(self.heap) == 0


# ---------------- STRING MATCHING: KMP ----------------

def kmp_search(text, pattern):
    if not pattern:
        return False

    lps = [0] * len(pattern)
    length = 0
    i = 1

    while i < len(pattern):
        if pattern[i] == pattern[length]:
            length += 1
            lps[i] = length
            i += 1
        elif length:
            length = lps[length - 1]
        else:
            i += 1

    i = 0
    j = 0

    while i < len(text):
        if text[i] == pattern[j]:
            i += 1
            j += 1

            if j == len(pattern):
                return True
        elif j:
            j = lps[j - 1]
        else:
            i += 1

    return False


# ---------------- TEXT PROCESSING ----------------

ALIASES = {
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "js": "javascript",
    "cpp": "c++",
    "react.js": "react",
    "node.js": "node"
}


def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#.]+", " ", text)
    return " ".join(text.split())


def canonical_skill(skill):
    skill = normalize(skill)
    return ALIASES.get(skill, skill)


def find_skill(text, skill):
    text = " " + normalize(text) + " "
    pattern = " " + normalize(skill) + " "
    return kmp_search(text, pattern)


# ---------------- RESUME EXTRACTION ----------------

def extract_text(file):
    data = file.getvalue()
    extension = file.name.lower().split(".")[-1]

    if extension == "pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    elif extension == "docx":
        document = Document(io.BytesIO(data))
        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

    elif extension == "txt":
        return data.decode("utf-8", errors="ignore")

    return ""


# ---------------- SCORING SYSTEM ----------------

def analyse_resume(name, resume, required, optional):
    skill_map = HashMap()

    for skill in required:
        skill_map.put(skill, "required")

    for skill in optional:
        skill_map.put(skill, "optional")

    matched_required = []
    missing_required = []
    matched_optional = []
    missing_optional = []

    for skill in skill_map.keys():
        found = find_skill(resume, skill)

        if skill_map.get(skill) == "required":
            if found:
                matched_required.append(skill)
            else:
                missing_required.append(skill)
        else:
            if found:
                matched_optional.append(skill)
            else:
                missing_optional.append(skill)

    required_score = (
        len(matched_required) / len(required) * 80
    )

    if optional:
        optional_score = (
            len(matched_optional) / len(optional) * 20
        )
    else:
        required_score = (
            len(matched_required) / len(required) * 100
        )
        optional_score = 0

    score = round(required_score + optional_score, 2)

    return {
        "name": name,
        "score": score,
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_optional": matched_optional,
        "missing_optional": missing_optional,
        "status": "Shortlisted" if score >= 70 else "Not Shortlisted"
    }


# ---------------- USER INTERFACE ----------------

st.markdown("""
<style>
.stApp {
    background: #101827;
    color: white;
}
[data-testid="stMetric"] {
    background: #1c2b43;
    padding: 15px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

st.title("📄 AI-Assisted Resume Shortlisting Tool")
st.caption("Smart Recruitment | Data Structures & Algorithms")

st.divider()

st.subheader("1. Job Requirements")

job_title = st.text_input(
    "Enter Job Title",
    placeholder="Example: Python Developer"
)

required_input = st.text_input(
    "Required Skills (comma separated)",
    placeholder="Python, SQL, Data Structures"
)

optional_input = st.text_input(
    "Optional Skills (comma separated)",
    placeholder="Machine Learning, HTML, React"
)

st.divider()

st.subheader("2. Upload Candidate Resumes")

files = st.file_uploader(
    "Upload multiple PDF, DOCX or TXT resumes",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True
)

if st.button("🚀 Analyse & Shortlist Resumes", use_container_width=True):

    required = list(dict.fromkeys(
        canonical_skill(x)
        for x in required_input.split(",")
        if x.strip()
    ))

    optional = list(dict.fromkeys(
        canonical_skill(x)
        for x in optional_input.split(",")
        if x.strip()
    ))

    if not job_title.strip():
        st.error("Please enter a job title.")

    elif not required:
        st.error("Please enter at least one required skill.")

    elif not files:
        st.error("Please upload at least one resume.")

    else:
        results = []
        errors = []

        for file in files:
            try:
                resume_text = extract_text(file)

                if not resume_text.strip():
                    errors.append(file.name + ": No readable text found")
                    continue

                result = analyse_resume(
                    file.name.rsplit(".", 1)[0],
                    resume_text,
                    required,
                    optional
                )

                results.append(result)

            except Exception as e:
                errors.append(file.name + ": " + str(e))

        if results:
            heap = MaxHeap()

            for index, result in enumerate(results):
                heap.push((result["score"], -index, result))

            ranked = []

            while not heap.is_empty():
                ranked.append(heap.pop()[2])

            st.session_state["results"] = ranked
            st.session_state["job_title"] = job_title

        else:
            st.session_state["results"] = []

        st.session_state["errors"] = errors


# ---------------- RESULTS ----------------

if "results" in st.session_state:

    results = st.session_state["results"]

    st.divider()
    st.header("3. Shortlisting Results")

    if results:
        shortlisted = [
            r for r in results
            if r["status"] == "Shortlisted"
        ]

        c1, c2, c3 = st.columns(3)

        c1.metric("Total Resumes", len(results))
        c2.metric("Shortlisted", len(shortlisted))
        c3.metric("Rejected", len(results) - len(shortlisted))

        st.subheader("Candidate Rankings")

        for rank, r in enumerate(results, 1):
            with st.expander(
                f"#{rank} {r['name']} | {r['score']}% | {r['status']}"
            ):
                st.progress(r["score"] / 100)

                st.write("**Matched Required Skills:**")
                st.success(", ".join(r["matched_required"]) or "None")

                st.write("**Missing Required Skills:**")
                st.error(", ".join(r["missing_required"]) or "None")

                st.write("**Matched Optional Skills:**")
                st.write(", ".join(r["matched_optional"]) or "None")

                st.write("**Missing Optional Skills:**")
                st.write(", ".join(r["missing_optional"]) or "None")

                st.write("**Final Status:**", r["status"])

        st.divider()
        st.subheader("4. Download Report")

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Rank", "Candidate", "Score",
            "Matched Skills", "Missing Skills", "Status"
        ])

        for rank, r in enumerate(results, 1):
            writer.writerow([
                rank,
                r["name"],
                r["score"],
                ", ".join(r["matched_required"]),
                ", ".join(r["missing_required"]),
                r["status"]
            ])

        st.download_button(
            "📥 Download CSV Report",
            output.getvalue(),
            file_name="shortlisting_results.csv",
            mime="text/csv",
            use_container_width=True
        )

    else:
        st.warning("No readable resumes were processed.")

    for error in st.session_state.get("errors", []):
        st.warning(error)


st.divider()
st.caption(
    "Academic demonstration tool. Shortlisting is based on "
    "skills matching and should be reviewed by a human recruiter."
)
