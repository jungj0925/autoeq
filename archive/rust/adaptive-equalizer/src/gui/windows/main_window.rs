use imgui::*;

pub struct MainWindow {
    visible: bool,
}

impl MainWindow {
    pub fn new() -> Self {
        Self { visible: true }
    }

    pub fn render(&mut self, ui: &Ui) {
        if !self.visible {
            return;
        }

        ui.window("Main Window")
            .size([300.0, 200.0], Condition::FirstUseEver)
            .build(|| {
                ui.text("Adaptive Equalizer");
                ui.separator();
                if ui.button("Settings") {
                    // We'll add settings later
                }
            });
    }
} 