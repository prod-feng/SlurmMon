/*
 * =========================================================
 * Dashboard tabs
 * =========================================================
 */

document.addEventListener("DOMContentLoaded", function () {

    const buttons = document.querySelectorAll(".tab-button");
    const panels = document.querySelectorAll(".tab-panel");

    buttons.forEach(function (button) {

        button.addEventListener("click", function () {

            const targetId = button.dataset.tab;

            buttons.forEach(function (item) {
                item.classList.remove("active");
                item.setAttribute(
                    "aria-selected",
                    "false"
                );
            });

            panels.forEach(function (panel) {
                panel.classList.remove("active");
                panel.hidden = true;
            });

            button.classList.add("active");

            button.setAttribute(
                "aria-selected",
                "true"
            );

            const target = document.getElementById(
                targetId
            );

            if (target) {
                target.hidden = false;
                target.classList.add("active");
            }

        });

    });


    /*
     * =====================================================
     * Table column selectors
     * =====================================================
     */

    const selectors = document.querySelectorAll(
        ".column-selector"
    );

    selectors.forEach(function (selector) {

        const button = selector.querySelector(
            ".column-selector-button"
        );

        const menu = selector.querySelector(
            ".column-selector-menu"
        );

        if (!button || !menu) {
            return;
        }


        /*
         * Find the table associated with this selector.
         */

        const tabPanel = selector.closest(
            ".tab-panel"
        );

        if (!tabPanel) {
            return;
        }

        const table = tabPanel.querySelector(
            "table[data-column-storage]"
        );

        if (!table) {
            return;
        }


        const storageKey =
            table.dataset.columnStorage;


        const checkboxes = selector.querySelectorAll(
            "input[data-column]"
        );


        /*
         * Open / close menu.
         */

        button.addEventListener(
            "click",
            function (event) {

                event.stopPropagation();

                const isOpen =
                    !menu.hidden;

                menu.hidden = isOpen;

                button.setAttribute(
                    "aria-expanded",
                    String(!isOpen)
                );

            }
        );


        /*
         * Close when clicking elsewhere.
         */

        document.addEventListener(
            "click",
            function (event) {

                if (!selector.contains(event.target)) {

                    menu.hidden = true;

                    button.setAttribute(
                        "aria-expanded",
                        "false"
                    );

                }

            }
        );


        /*
         * Apply visibility to a column.
         */

        function setColumnVisibility(
            column,
            visible
        ) {

            const cells = table.querySelectorAll(
                '[data-column="' +
                column +
                '"]'
            );

            cells.forEach(function (cell) {

                cell.style.display =
                    visible ? "" : "none";

            });

        }


        /*
         * Get current visible columns.
         */

        function getVisibleColumns() {

            const visible = [];

            checkboxes.forEach(function (checkbox) {

                if (checkbox.checked) {
                    visible.push(
                        checkbox.dataset.column
                    );
                }

            });

            return visible;
        }


        /*
         * Save selection.
         */

        function saveColumns() {

            const visible =
                getVisibleColumns();

            try {

                localStorage.setItem(
                    storageKey,
                    JSON.stringify(visible)
                );

            } catch (error) {

                /*
                 * localStorage may be disabled.
                 * The table still works without it.
                 */

            }

        }


        /*
         * Prevent hiding every column.
         */

        function ensureOneColumnVisible(
            changedCheckbox
        ) {

            const visible =
                getVisibleColumns();

            if (visible.length === 0) {

                changedCheckbox.checked = true;

                return false;
            }

            return true;
        }


        /*
         * Restore saved selection.
         */

        function restoreColumns() {

            let saved = null;

            try {

                const value =
                    localStorage.getItem(
                        storageKey
                    );

                if (value) {
                    saved = JSON.parse(value);
                }

            } catch (error) {

                saved = null;

            }


            if (!Array.isArray(saved)) {
                return;
            }


            checkboxes.forEach(function (checkbox) {

                checkbox.checked =
                    saved.includes(
                        checkbox.dataset.column
                    );

            });


            /*
             * Make sure at least one column
             * remains visible.
             */

            if (getVisibleColumns().length === 0) {

                checkboxes[0].checked = true;

            }


            checkboxes.forEach(function (checkbox) {

                setColumnVisibility(
                    checkbox.dataset.column,
                    checkbox.checked
                );

            });

        }


        /*
         * Checkbox changes.
         */

        checkboxes.forEach(function (checkbox) {

            checkbox.addEventListener(
                "change",
                function () {

                    if (
                        !ensureOneColumnVisible(
                            checkbox
                        )
                    ) {
                        return;
                    }

                    setColumnVisibility(
                        checkbox.dataset.column,
                        checkbox.checked
                    );

                    saveColumns();

                }
            );

        });


        /*
         * Reset button.
         */

        const resetButton =
            selector.querySelector(
                ".column-selector-reset"
            );

        if (resetButton) {

            resetButton.addEventListener(
                "click",
                function () {

                    checkboxes.forEach(
                        function (checkbox) {

                            checkbox.checked = true;

                            setColumnVisibility(
                                checkbox.dataset.column,
                                true
                            );

                        }
                    );

                    saveColumns();

                }
            );

        }


        /*
         * Initial state.
         */

        restoreColumns();

    });

});



document.addEventListener("DOMContentLoaded", function () {

    const buttons = document.querySelectorAll(".tab-button");
    const panels = document.querySelectorAll(".tab-panel");
    const metricLinks = document.querySelectorAll(
        ".metric-card-link[data-open-tab]"
    );


    function activateTab(targetId) {

        const targetPanel = document.getElementById(targetId);

        if (!targetPanel) {
            return;
        }

        buttons.forEach(function (button) {

            const isActive =
                button.dataset.tab === targetId;

            button.classList.toggle(
                "active",
                isActive
            );

            button.setAttribute(
                "aria-selected",
                isActive ? "true" : "false"
            );

        });


        panels.forEach(function (panel) {

            const isActive =
                panel.id === targetId;

            panel.classList.toggle(
                "active",
                isActive
            );

            panel.hidden = !isActive;

        });

    }


    /*
     * Normal tab buttons
     */

    buttons.forEach(function (button) {

        button.addEventListener("click", function () {

            const targetId = button.dataset.tab;

            activateTab(targetId);

            history.replaceState(
                null,
                "",
                "#" + targetId
            );

        });

    });


    /*
     * Summary metric cards
     */

    metricLinks.forEach(function (link) {

        link.addEventListener("click", function (event) {

            event.preventDefault();

            const targetId = link.dataset.openTab;

            activateTab(targetId);

            history.replaceState(
                null,
                "",
                "#" + targetId
            );

        });

    });


    /*
     * Open a tab directly when the URL contains a hash.
     *
     * Example:
     * /accounts/#tab-qos
     */

    const hash = window.location.hash;

    if (hash) {

        const targetId = hash.substring(1);

        if (document.getElementById(targetId)) {
            activateTab(targetId);
        }

    }

});

