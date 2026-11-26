# Written by ahmed khalil ahmed.khalil@areasciencepark.it
#
# Import modules for file system operations (os), JSON parsing (json), 
# and regular expressions -- regex (re)
import os, json, re

# Import PIL for image loading and matplotlib for visualization
from PIL import Image
import matplotlib
matplotlib.use("Agg")   # draw into files only: a container or a server has no screen
import matplotlib.pyplot as plt


# Class for visualizing SEM images alongside selected metadata
class SEMVisualizer:
    def __init__(self, json_path, image_path, output_dir="./output", variables=None):
        # Store the path to the cleaned metadata JSON file
        self.json_path = json_path
        
        # Store the path to the SEM image file
        self.image_path = image_path

        # Store the folder where the figure is saved
        self.output_dir = output_dir
        
        # Define the list of metadata variables to extract and display
        # (the default below, unless another list is given)
        self.variables = variables or [
            "AP_WD",
            "AP_BEAM_TIME",
            "AP_IMAGE_PIXEL_SIZE",
            "AP_HOLDER_HEIGHT",
            "AP_BEAM_CURRENT",
            "AP_HOLDER_DIAMETER"]        
        
        # Initialize an empty dictionary to hold loaded metadata
        self.metadata = {}
        

    # Load metadata from JSON file into self.metadata
    def load_metadata(self):
        with open(self.json_path, 'r') as f:
            self.metadata = json.load(f)


    def clean_value(self, raw_value, variable_name=None):
        """
        Splits a cleaned metadata value into its number and unit.

        The value should be a (signed) number, optionally in scientific
        notation, followed by a unit. A text value (e.g. a detector name)
        is kept as it is, without a unit.

        Examples:
            "3.18 mm"             ->  ("3.18", "mm")
            "-13 pA"              ->  ("-13", "pA")
            "2.34e-006 mbar"      ->  ("2.34e-006", "mbar")
            "Detector = InLens"   ->  ("InLens", "")
            missing (None, N/A)   ->  ("N/A", "N/A")

        Returns:
            (value, unit) as strings
        """

        # Ensure the input is a string before applying regex
        if not isinstance(raw_value, str) or raw_value == "N/A":
            return ("N/A", "N/A")

        # Use regex to match a signed number (optionally in scientific notation)
        # followed by its unit, e.g. '-13 pA', '2.34e-006 mbar'
        match = re.fullmatch(
            r'([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*([^\d\s].*)', raw_value.strip())

        # If a match is found, return the value and the unit
        if match:
            value, unit = match.groups()
            return (value, unit)

        # Otherwise it is a text value: keep the part after "=" (if any), with no unit
        text = raw_value.split("=", 1)[-1].strip()
        return (text, "") if text else ("N/A", "N/A")


    def extract_variables(self):
        """
        Extracts selected metadata variables and formats
        them into (name, value, unit) tuples for display.
        """
        
        # Initialize list to hold formatted variable rows
        rows = []
        
        # Iterate over each variable of interest
        for var in self.variables:
            # Get raw value from metadata dictionary
            raw = self.metadata.get(var, "N/A")
            
            # Clean and split into value and unit
            value, unit = self.clean_value(raw, variable_name=var)
            
            # Append formatted tuple to the table rows
            rows.append((var, value, unit))
        
        # Return the list of formatted metadata rows
        return rows
        

    def show_image_with_table(self):
        """
        Displays the SEM image alongside a formatted metadata
        table and saves the combined output as a figure.
        """
        
        # Load metadata from JSON into self.metadata
        self.load_metadata()
        
        # Extract and format selected metadata variables
        table_data = self.extract_variables()
        
        # Extract image name (without extension) for output naming
        image_name = os.path.splitext(os.path.basename(self.image_path))[0]

        # Load the SEM image using PIL
        img = Image.open(self.image_path)

        # Create a figure with two vertically stacked subplots.
        # The table part grows with the number of rows, so any list of keys fits.
        n_rows = len(table_data) + 1                       # + the header row
        table_height = 0.42 * n_rows                       # inches
        fig, (ax_img, ax_table) = plt.subplots(
            2, 1, figsize=(8, 5 + table_height),
            gridspec_kw={'height_ratios': [5, table_height]})

        # Display the SEM image in grayscale
        ax_img.imshow(img, cmap='gray')
        ax_img.axis('off')
        ax_img.set_title("SEM Image", fontsize=14)

        # Display the metadata table with column headers.
        # bbox=[0, 0, 1, 1] makes the table fill its axes exactly, so the title
        # above it never overlaps the table, however many rows it has.
        table = ax_table.table(cellText=table_data, colLabels=["Variable", "Value", "Unit"],
                               cellLoc='center', bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        for (row, _), cell in table.get_celld().items():   # bold header row
            if row == 0:
                cell.set_text_props(weight='bold')
                cell.set_facecolor('#EEF2FA')
        ax_table.axis('off')
        ax_table.set_title("Extracted Metadata", fontsize=12, pad=10)

        # Adjust layout to prevent overlap
        plt.tight_layout()
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save the figure as a PNG image
        figure_path = os.path.join(self.output_dir, f"{image_name}.png")
        plt.savefig(figure_path, dpi=150, bbox_inches='tight')
        
        # Display the figure (not in a pipeline: there is no screen)
        # plt.show()

        # Close the figure to free its memory (many images in one run)
        plt.close(fig)

        # Print the same table in the terminal
        self.print_table(table_data)

        return figure_path


    def print_table(self, table_data=None):
        """
        Prints the selected metadata as a text table in the terminal.

        Example:
            Variable              Value      Unit
            --------------------  ---------  ----
            AP_WD                 3.18       mm
        """

        # Use the given rows, or load and extract them
        if table_data is None:
            self.load_metadata()
            table_data = self.extract_variables()

        # Print the header and one line per variable
        print(f"  {'Variable':<22} {'Value':<12} Unit")
        print(f"  {'-' * 22} {'-' * 12} {'-' * 6}")
        for var, value, unit in table_data:
            print(f"  {var:<22} {value:<12} {unit}")
