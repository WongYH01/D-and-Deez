import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Narration } from "@/play/Narration";

describe("Narration", () => {
  it("renders bold, italic and lists", () => {
    const { container } = render(<Narration text={"The **king** is *angry*.\n\n- sword\n- shield"} />);
    expect(container.querySelector("strong")?.textContent).toBe("king");
    expect(container.querySelector("em")?.textContent).toBe("angry");
    expect(container.querySelectorAll("li")).toHaveLength(2);
  });

  it("renders partial markdown mid-stream without throwing", () => {
    const { container } = render(<Narration text={"The **king"} />);
    expect(container.textContent).toContain("king");
  });

  it("never executes or inserts raw HTML", () => {
    const { container } = render(
      <Narration text={'Hi <script>window.__pwned = 1</script><img src=x onerror="window.__pwned = 1"> there'} />,
    );
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect((window as unknown as { __pwned?: number }).__pwned).toBeUndefined();
    expect(screen.getByText(/there/)).toBeTruthy();
  });

  it("does not turn a javascript: link into a live href", () => {
    const { container } = render(<Narration text="[click](javascript:alert(1))" />);
    const a = container.querySelector("a");
    expect(a?.getAttribute("href") ?? "").not.toMatch(/^javascript:/i);
  });
});
