export function About() {
  return (
    <article className="space-y-4 font-serif leading-relaxed">
      <h1 className="font-heading text-2xl">About</h1>
      <p>
        D and Deez is a single-player, text-based tabletop adventure. Claude narrates; the app's code
        referees the rules and plans the story.
      </p>
      <h2 className="font-heading text-xl">System Reference Document</h2>
      <p>
        This work includes material taken from the System Reference Document 5.1 ("SRD 5.1") by Wizards of
        the Coast LLC and available at{" "}
        <a className="text-primary underline" href="https://dnd.wizards.com/resources/systems-reference-document">
          https://dnd.wizards.com/resources/systems-reference-document
        </a>
        . The SRD 5.1 is licensed under the Creative Commons Attribution 4.0 International License available at{" "}
        <a className="text-primary underline" href="https://creativecommons.org/licenses/by/4.0/legalcode">
          https://creativecommons.org/licenses/by/4.0/legalcode
        </a>
        .
      </p>
    </article>
  );
}
