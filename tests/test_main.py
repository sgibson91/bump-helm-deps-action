from helm_bot.main import split_str_to_list


def test_split_str_to_list_simple():
    test_str1 = "label1,label2"
    test_str2 = "label1 , label2"

    expected_output = ["label1", "label2"]

    result1 = split_str_to_list(test_str1)
    result2 = split_str_to_list(test_str2)

    assert result1 == expected_output
    assert result2 == expected_output
    assert result1 == result2


def test_split_str_to_list_complex():
    test_str1 = "type: feature,impact: low"
    test_str2 = "type: feature , impact: low"

    expected_output = ["type: feature", "impact: low"]

    result1 = split_str_to_list(test_str1)
    result2 = split_str_to_list(test_str2)

    assert result1 == expected_output
    assert result2 == expected_output
    assert result1 == result2
