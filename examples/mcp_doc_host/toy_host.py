"""Toy host/client/server, standalone (no MCP SDK, no cloud services, no vector database) - just
enough to demonstrate the role/kind/peer conventions this example's
flowlog.config.json is built for. Run it with flowlog:

    flowlog run examples/mcp_doc_host/toy_host.py -- "How do I rotate an API key?"

It follows the usual MCP host/client/server shape, trimmed to a few
in-process calls so anyone can see the viewer working without setting up
a real MCP stack.
"""
import sys
import time

import flowlog


def discover() -> list[str]:
    flowlog.send("CLIENT", "SERVER", "server/discover", kind="discover")
    time.sleep(0.05)
    tools = ["docs_search", "ticket_search"]
    flowlog.recv("CLIENT", "SERVER", f"{len(tools)} tools: {', '.join(tools)}", kind="tools_list_result",
                 payload={"tools": tools})
    return tools


def ask_model_which_tool(question: str, tools: list[str]) -> str:
    flowlog.send("HOST", "LLM", f"{question} | which of {tools} fits?", kind="llm_tool_request",
                 payload={"question": question, "tools": tools})
    time.sleep(0.05)
    choice = tools[0]
    flowlog.recv("HOST", "LLM", f"call {choice}", kind="llm_tool_call", payload={"tool_call": {"name": choice}})
    return choice


def call_tool(name: str, query: str) -> dict:
    flowlog.send("CLIENT", "SERVER", f"tools/call {name}", kind="tool_call", payload={"name": name, "arguments": {"query": query}})
    flowlog.event("SERVER", "send", "BACKEND", f"search index: {query}", kind="backend_search", payload={"query": query})
    time.sleep(0.05)
    chunks = [{"title": "API key rotation guide"}]
    flowlog.event("SERVER", "recv", "BACKEND", f"{len(chunks)} ranked chunk(s)", kind="backend_result", payload={"chunks": chunks})
    flowlog.recv("CLIENT", "SERVER", f"result: {len(chunks)} chunk(s)", kind="tool_result",
                 payload={"results": chunks})
    return {"results": chunks}


def write_answer(question: str, result: dict) -> str:
    flowlog.send("HOST", "LLM", "write a cited answer from the tool result", kind="llm_answer_request",
                 payload={"question": question, "result": result})
    time.sleep(0.05)
    answer = f"Here is how to rotate the key, per {result['results'][0]['title']}."
    flowlog.recv("HOST", "LLM", f"answer, {len(answer)} chars", kind="llm_answer_reply", payload={"answer": answer})
    return answer


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else "How do I rotate an API key?"
    flowlog.note("HOST", f"question: {question}", kind="question", payload={"question": question})
    tools = discover()
    choice = ask_model_which_tool(question, tools)
    result = call_tool(choice, question)
    answer = write_answer(question, result)
    flowlog.event("HOST", "send", "OPERATOR", answer, kind="answer", payload={"answer": answer})
    print(answer)


if __name__ == "__main__":
    main()
