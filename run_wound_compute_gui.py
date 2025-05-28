import sys
sys.path.insert(1, '/projectnb/lejlab2/quan/wound_compute_GUI/woundcomputeGUI/src')
import woundcomputegui.main_gui as mg

# Main function to run the application
def main():
    app = mg.QApplication(sys.argv)
    window = mg.MyWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()