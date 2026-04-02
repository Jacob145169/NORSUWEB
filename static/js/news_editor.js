document.addEventListener("DOMContentLoaded", () => {
    if (!window.tinymce) {
        return;
    }

    document.querySelectorAll('textarea[data-richtext-editor="tinymce"]').forEach((field) => {
        if (field.dataset.tinymceInitialized === "true") {
            return;
        }

        field.dataset.tinymceInitialized = "true";

        tinymce.init({
            target: field,
            license_key: "gpl",
            menubar: "file edit view insert format tools table help",
            plugins: "advlist autolink lists link preview table code wordcount charmap",
            toolbar:
                "undo redo | blocks | fontfamily fontsize | bold italic underline | forecolor | " +
                "alignleft aligncenter alignright alignjustify | bullist numlist | " +
                "link blockquote table | preview code removeformat",
            toolbar_mode: "sliding",
            min_height: 420,
            resize: true,
            browser_spellcheck: true,
            contextmenu: false,
            link_default_protocol: "https",
            block_formats: "Paragraph=p; Heading 1=h1; Heading 2=h2; Heading 3=h3; Blockquote=blockquote",
            font_family_formats:
                "Arial=arial,helvetica,sans-serif; Georgia=georgia,palatino,serif; " +
                "Tahoma=tahoma,arial,helvetica,sans-serif; Times New Roman=times new roman,times,serif; " +
                "Verdana=verdana,geneva,sans-serif",
            font_size_formats: "10px 12px 14px 16px 18px 20px 24px 30px 36px",
            content_style:
                "body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 16px; line-height: 1.7; padding: 1rem; } " +
                "p, ul, ol, blockquote, table { margin-bottom: 1rem; } " +
                "blockquote { border-left: 4px solid #d4a63d; margin-left: 0; padding-left: 1rem; color: #314157; } " +
                "table { border-collapse: collapse; width: 100%; } th, td { border: 1px solid #d7dee8; padding: 0.65rem 0.75rem; vertical-align: top; }",
            setup: (editor) => {
                const syncContent = () => editor.save();

                editor.on("change input undo redo keyup", syncContent);
            },
        });
    });
});
