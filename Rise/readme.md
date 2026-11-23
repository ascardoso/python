For a `.md` (Markdown) file, use **dollar signs** to wrap LaTeX expressions.

There are two main formats:

## **1. Inline mathematics**

Use a single `$` on each side:

```
The fundamental frequency is $f_0 = 440\text{ Hz}$.
```

Displays as:

The fundamental frequency is \\(f_0 = 440\text{ Hz}\\).

## **2. Block mathematics**

Use double dollar signs on separate lines:

```
$$
x(t) = \sum_{n=1}^{N} A_n \sin(2\pi n f_0 t + \phi_n)
$$
```

This displays as a centered equation:

\\[ x(t) = \sum\_{n=1}^{N} A_n \sin(2\pi n f_0 t + \phi_n) \\]

## **3. Multiple equations**

You can also use `aligned` for neatly arranged equations:

```
$$
\begin{aligned}
x(t) &= \sum_{n=1}^{N} A_n \sin(2\pi n f_0 t) \\
f_n &= n f_0
\end{aligned}
$$
```

## **Important: GitHub Markdown**

GitHub supports LaTeX math rendering natively, including:

| Syntax    | Purpose             |
| --------- | ------------------- |
| `$...$`   | Inline equation     |
| `$$...$$` | Display equation    |
| `\(...\)` | Inline alternative  |
| `\[...\]` | Display alternative |

**My recommendation:** Use `$...$` and `$$...$$` in your README files. They're widely supported and work particularly well on GitHub.

One caveat: ordinary Markdown viewers don't necessarily support LaTeX. GitHub does, but some local editors require a MathJax or KaTeX extension.

Ah, that's because the Markdown renderer you're using isn't interpreting the LaTeX delimiters, so it's displaying them literally.

For GitHub README files, use:

```
The fundamental frequency is $f_0 = 440\text{ Hz}$.
```

For a centered equation:

```
$$
f_0 = 440\text{ Hz}
$$
```

**Important distinction:** GitHub supports both formats, but ChatGPT and some Markdown previewers use different rendering rules.

If you're seeing `\(f_0 = 440\text{ Hz}\)` literally here, that's a limitation of the current display renderer, not an error in the LaTeX itself.