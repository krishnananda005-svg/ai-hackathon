from engine import search

queries = [
    "Where is the health centre?",
    "What time does the library open?",
    "How do I register for an event?",
    "I lost my ID card, what should I do?",
    "Where is the CTS office?",
    "How many books can a UG student borrow?",
    "What are the lab timings?",
    "How do I contact the men's hostel office?",
    "What are the timings?",
    "Who will win the IPL?",
    "What is my CGPA?",
    "hi",
    "asdfgh",
        "When are the labs open?",
    "Where is room AB1-201?",
    "What is the B.Tech fee?",
    "Where is the nearest ATM?",
    "bus timings",
    "How do I apply for hostel?",
    "What's the weather today?",
]

for q in queries:
    r = search(q)
    print(f"Q: {q}")
    print(f"   status={r['status']}  score={r['score']:.2f}  id={r['id']}  title={r['title']}")
    print(f"   source={r['source']}  verified={r['verified']}  suggestions={r['suggestions']}\n")