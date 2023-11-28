import {WeyaElement, WeyaElementFunction} from "../../../../lib/weya/weya"
import EditableField, {EditableFieldOptions} from "./editable_field"
import {CustomButton} from "../buttons"
import {getTimeString} from "../../utils/time"

interface DatePickerOptions extends EditableFieldOptions {
    min: Date
    max: Date
}

class DatePicker extends  EditableField {
    inputElem: HTMLInputElement
    value: string
    min: string
    max: string

    constructor(opt: DatePickerOptions) {
        super(opt)
        this.value = opt.value
        this.max = getTimeString(opt.max)
        this.min = getTimeString(opt.min)
    }

    public getInput(): string {
        let date = new Date(this.inputElem.value);
        return (date.getTime()/ 1000).toString() // convert to python timestamp
    }

    public updateValue(value: string) {
        this.inputElem.value = value
    }

    render($: WeyaElementFunction) {
        console.log(this.min, this.max, this.value)
        $('div.input-container', $ => {
            $('div.input-content', $ => {
                this.inputElem = <HTMLInputElement>$('input', {
                            type: "datetime-local",
                            value: this.value,
                            min: `${this.min}`,
                            max: `${this.max}`,
                        }
                    )
            })
        })
    }
}

interface DateRangeFieldOptions {
    min: number
    max: number
    onClick: (min: number, max: number) => void
    buttonLabel: string
    minDate: Date
    maxDate: Date
}

export class DateRangeField {

    private readonly minField: DatePicker
    private readonly maxField: DatePicker
    private readonly onClick: (min: number, max: number) => void
    private readonly doneButton: CustomButton
    private elem: WeyaElement
    private min: number
    private max: number
    private minDate: Date
    private maxDate: Date

    constructor(opt: DateRangeFieldOptions) {
        this.onClick = opt.onClick
        this.min = opt.min
        this.max = opt.max
        console.log(this.min, this.max)
        this.minDate = opt.minDate
        this.maxDate = opt.maxDate
        this.minField = new DatePicker({name: "", value: `${this.min}`, min: this.minDate, max: this.maxDate})
        this.maxField = new DatePicker({name: "", value: `${this.max}`, min: this.minDate, max: this.maxDate})
        this.doneButton = new CustomButton({
            onButtonClick: () => {
                let range: number[] = this.getRange()
                this.onClick(range[0], range[1])
            }, parent: this.constructor.name, text: opt.buttonLabel, noMargin: true
        })
    }

    public getRange(): [number, number] {
        let min = this.minField.getInput() == '' ? -1 : parseFloat(this.minField.getInput())
        let max = this.maxField.getInput() == '' ? -1 : parseFloat(this.maxField.getInput())

        this.min = min
        this.max = max

        return [min, max]
    }

    public setRange(min: number, max: number) {
        this.min = min
        this.max = max

        console.log(min, max)

        if (this.elem == null || !this.minField.valueElem) { //element is not yet rendered or destroyed
            return
        }

        this.minField.updateValue(min == -1 || isNaN(this.min) ? getTimeString(new Date(0)) : getTimeString(new Date(min * 1000)))
        this.maxField.updateValue(min == -1 || isNaN(this.max) ? getTimeString(new Date()) : getTimeString(new Date(max * 1000)))
    }

    render($: WeyaElementFunction) {
        this.minField.value = this.min == -1 || isNaN(this.min) ? getTimeString(new Date(0)) : getTimeString(new Date(this.min * 1000))
        this.maxField.value = this.min == -1 || isNaN(this.max) ? getTimeString(new Date()) : getTimeString(new Date(this.max * 1000))

        this.elem = $('div.range-field', $=> {
            this.minField.render($)
            this.maxField.render($)
            this.doneButton.render($)
        })
    }
}