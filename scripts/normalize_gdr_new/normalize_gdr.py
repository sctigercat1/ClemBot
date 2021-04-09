import csv
from collections import Counter
import re

"""

This script attempts to normalize and correct errors in the Clemson Grade Distribution Reports. To use this script:

1. Download PDFs from Clemson OIR
2. Convert to CSV using Tabula: https://tabula.technology/ (exclude column titles and footer text)
3. Run this script on the generated CSVs.

Things are generally okay from 2013Fall to 2019Spring.
2019Fall has name formatting issues.
2020Spring is excluded due to the SCP/SCN/SCD which might artificially deflate B/C/Ds.
2020Fall has multiple formatting issues.

"""

# Constants
file_name = "./raw-csv/tabula-%d%s.csv"  # tabula-2013Fall
new_file = "./csv/%d_%s.csv"  # 2013Fall

LAST_NAME_DUPLICATES = ("van", "vander")  # Only used in 2018, 2020. Make sure it's lowercase

# Manual override
SPECIAL_SHORT_NAMES = {
    "Van den Hurk Peter": "Peter Van den Hurk",
    "Jayasekara Merenchige Pubudu Lakmal Wijesiri": "Pubudu Jayasekara Merenchige"
}

files = {
    2013: ["Fall"],
    2014: ["Fall", "Spring"],
    2015: ["Fall", "Spring"],
    2016: ["Fall", "Spring"],
    2017: ["Fall", "Spring"],
    2018: ["Fall", "Spring"],
    2019: ["Fall", "Spring"],
    2020: ["Fall"]
}


# Adjust values of each column for standardization
def general_formatting(row, year):
    # Stabilize Honors column
    if row[-1] not in ("", "H"):
        row.append("")
    if row[-1] == "H":
        row[-1] = True

    # Add CourseId and Year
    row.append(row[0] + "-" + row[1])
    row.append(year)

    # Adjust prof names
    """
    if year not in (2018, 2020):
        names = row[12].replace(".", "").split(',')
        last_name = names[0]
        first_names = " ".join(names[1:])
    else:
        names = row[12].replace(".", "").split()
        if names[0].lower() in LAST_NAME_DUPLICATES:
            last_name = names[0] + " " + names[1]
            first_names = " ".join(names[2:])
        else:
            last_name = names[0]
            first_names = " ".join(names[1:])
    """



    """
    # Change instructor from Last, First MI to First MI Last
    name = row[12].replace(".", "").split()
    if year in (2018, 2020):
        last_name = name[0]
    else:
        last_name = name[0][:-1]  # Remove comma
    first_names = " ".join(name[1:])  # Select all names e.g. first middle 1 middle 2
    row[12] = first_names + " " + last_name
    """

    # Convert xx% to 0.xx
    for cell in range(4, 12):
        row[cell] = float(row[cell][:-1]) / 100.0

    return row


# Fix formatting issue associated with the PDF --> CSV conversion
def combine_remnant_names(read, year):
    final_rows = []

    if year > 2019:
        name_row = 16
    else:
        name_row = 12

    current_remnant_name = ""
    for row in read:
        if row[0] == "" and row[name_row] != "":
            current_remnant_name += " " + row[name_row]
        elif row[0] != "":
            if current_remnant_name != "":
                if final_rows[-1][name_row][-1] == "-":
                    current_remnant_name = current_remnant_name[1:]
                final_rows[-1][name_row] += current_remnant_name
                current_remnant_name = ""

            final_rows.append(row)
    else:
        # End
        if current_remnant_name != "":
            if final_rows[-1][name_row][-1] == "-":
                current_remnant_name = current_remnant_name[1:]
            final_rows[-1][name_row] += current_remnant_name
            current_remnant_name = ""

    return final_rows

# Remove all middle names, except when 2+ profs have the same first and last name in a given semester
def analyze_names(rows):
    def shorten_name(name):
        """
        names = name.split()
        firstname = names[0]
        lastname = names[-1]

        # Special cases
        # Single digit first name - skip
        if len(names[0]) == 1 and len(names) > 2:
            firstname = names[1]
        # Double last name
        if names[-2].lower() in LAST_NAME_DUPLICATES:
            lastname = " ".join(names[-2:]) # Join last 2 items of list

        return firstname + " " + lastname
        """

        if name in [*SPECIAL_SHORT_NAMES]:
            return SPECIAL_SHORT_NAMES[name]

        firstname = ""
        if "," in name:
            names = name.replace(".", "").split(',')
            firstname = ""
            if len(names) > 1 and len(names[1]) > 0:
                firstname = names[1].split()[0]

            lastname = names[0]
            test_lastname = lastname.split()
            if len(test_lastname) > 1 and len(test_lastname[1]) == 1:
                lastname = test_lastname[0]
        else:
            # Van Scoy Roger Larry
            names = name.replace(".", "").split()
            firstname = ""
            if len(names) > 1:
                firstname = names[1]
            if len(firstname) == 1 and len(names) > 2:
                firstname = names[2]

            lastname = names[0]
            for searches in LAST_NAME_DUPLICATES:
                if re.search(r'^' + searches + r'$', names[0].lower()):
                    lastname = " ".join(names[0:2])
                    firstname = names[2]

        return " ".join([firstname, lastname]).strip()


    full_names = []
    firstlast_names = []
    duplicate_full_names = []
    final_rows = []

    for row in rows:
        full_names.append(row[12])
        firstlast_names.append(shorten_name(row[12]))

        #if "Jayasekara" in row[12]:
            #print(row)
            #print(shorten_name(row[12]))
            #import sys; sys.exit()

    firstlast_counts = Counter(firstlast_names)
    full_counts = Counter(full_names)

    for name in full_names:
        count1 = full_counts[name]
        first_last_name = shorten_name(name)
        count2 = firstlast_counts[first_last_name]
        #print(name)
        #print(first_last_name)
        #import sys; sys.exit()

        if count2 - count1 != 0:
            duplicate_full_names.append(name)

    for row in rows:
        if row[12] not in duplicate_full_names:
            row[12] = shorten_name(row[12])

        final_rows.append(row)

    print(duplicate_full_names)
    return final_rows


# Start creating normalized CSVs
for year, semesters in files.items():
    for semester in semesters:
        with open(file_name % (year, semester), 'r') as csv_read:
            with open(new_file % (year, semester), 'w', newline='') as csv_write:
                # Write initial row
                writer = csv.writer(csv_write)
                writer.writerow(
                    ["Course", "Number", "Section", "Title", "A", "B", "C", "D", "F", "P", "F(P)", "W", "Instructor",
                     "Honors", "CourseId", "Year"])

                read = csv.reader(csv_read, delimiter=',')
                if semester == "Fall" and (year == 2019 or year == 2020):
                    read = combine_remnant_names(read, year)

                final_rows = []
                for row in read:
                    if year == 2020 and semester == "Fall":
                        # Remove SCP/SCN/SCD/I
                        row = row[0:12] + row[16:18]

                        # Replace #### with 100%
                        row = ["100%" if x == "####" else x for x in row]

                    final_rows.append(general_formatting(row, year))

                # Shorten to first last, save any profs with duplicate names
                final_rows = analyze_names(final_rows)

                for row in final_rows:
                    # Write
                    writer.writerow(row)

        print("Finished %d%s" % (year, semester))

print("Done")
