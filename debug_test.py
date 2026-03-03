import os
import sys

# Add the Codes directory to path
sys.path.append(os.path.join(os.getcwd(), "Codes"))

# Use the same setup as agent.py
import agent

# Set env vars for the test (using real keys from context)
os.environ["TFY_API_KEY"] = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkdyR2VuTWlpWEhYREx4UlFPQ0otWXhBUXZtNCJ9.eyJhdWQiOiI2OTZlNmU2Zi03NjYxLTYzNjMtNjU3Mi0zYTY0MzIzNjY1NjMiLCJleHAiOjM3MzE1ODQwMjUsImlhdCI6MTc3MjAzMjAyNSwiaXNzIjoidHJ1ZWZvdW5kcnkuY29tIiwic3ViIjoiY21tMjY0NWhxNzN4aDAxbm00d2Q4Ym0wMSIsImp0aSI6ImNtbTI2NDVoczczeGkwMW5tZDRjYzh6ZzEiLCJzdWJqZWN0U2x1ZyI6ImRlZmF1bHQtY21tMjYzc2JoNXppajAxcWJmdjF5aGowdiIsInVzZXJuYW1lIjoiZGVmYXVsdC1jbW0yNjNzYmg1emlqMDFxYmZ2MXloajB2IiwidXNlclR5cGUiOiJzZXJ2aWNlYWNjb3VudCIsInN1YmplY3RUeXBlIjoic2VydmljZWFjY291bnQiLCJ0ZW5hbnROYW1lIjoiaW5ub3ZhY2NlciIsInJvbGVzIjpbXSwiand0SWQiOiJjbW0yNjQ1aHM3M3hp0DFubWQ0Y2M4emcxIiwiYXBwbGljYXRpb25JZCI6IjY5NmU2ZTZmLTc2NjEtNjM2My02NTcyLTNhNjQzMjM2NjU2MyJ9.Jdb2qq1alKSboc703Jp88GQYzEsEtGOdEYUvp8UcS5SYQ9p2KZtG7hAQbVMQEXotiDjnsOlPtX6N-nPSLVCPxteKYjG2D6vsdRokGYMoS6zIreP7uCpgrUZKtDLdxAtvFofM4TJCJMr1MqeYI6JnBZtlYbg4NiHBWEzuRBtNYrUWUaL7qMecq04aSfOdBSOlAUbydvgN1pz0bVcyHe6MTzzhnhs0EE3wZBuwHOfxe-el-Gu3YHAN476pK51k7ZwaywwS-fhFoS6WWQpXoU6BhsGovqQyn85dcZtXX-zJn5wDPQ-R2iudm_cglY0953AIxryA7lvWDYGnBafm6_bFXw"
os.environ["TFY_BASE_URL"] = "https://truefoundry.innovaccer.com/api/llm"

print("Starting debug test for first 3 accounts...")
accounts = agent.load_accounts(agent.ACCOUNT_LIST_PATH)
accounts = sorted(accounts, key=lambda x: 0 if x['tier'] == 'Strategics' else 1 if x['tier'] == 'Top' else 2)

for acc in accounts[:3]:
    print(f"Testing: {acc['name']} ({acc['tier']})")
    res = agent.search_with_truefoundry(acc['name'], os.environ["TFY_API_KEY"], os.environ["TFY_BASE_URL"])
    print(f"Result Score: {res.get('score', 0)}")
