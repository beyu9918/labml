import d3 from "../../../d3"
import {WeyaElementFunction} from '../../../../../lib/weya/weya'
import {PointValue} from "../../../models/run"
import {getBaseColor} from "../constants"
import {getExtent, getScale, getSelectedIdx} from "../utils"
import {LineFill, LinePlot} from "../lines/plot"
import {formatFixed} from "../../../utils/value"

export interface StandaloneSparkLineOptions {
    name: string
    series: PointValue[]
    width: number
    stepExtent: [number, number]
}

export interface SparkLineOptions extends StandaloneSparkLineOptions {
    selected: number
    minLastValue: number
    maxLastValue: number
    onClick?: () => void
    isMouseMoveOpt?: boolean
    color: string
    showValue?: boolean
}

export class SparkLine {
    series: PointValue[]
    name: string
    minLastValue: number
    maxLastValue: number
    color: string
    selected: number
    titleWidth: number
    chartWidth: number
    onClick?: () => void
    isMouseMoveOpt?: boolean
    primaryElem: SVGTextElement
    secondaryElem: SVGTextElement
    className: string = 'empty'
    xScale: d3.ScaleLinear<number, number>
    yScale: d3.ScaleLinear<number, number>
    bisect: d3.Bisector<number, number>
    linePlot: LinePlot
    showValue: Boolean

    constructor(opt: SparkLineOptions) {
        this.series = opt.series

        if (opt.selected == -1) {
            this.series = [this.series[this.series.length - 1]]
        }

        this.name = opt.name
        this.selected = opt.selected
        this.onClick = opt.onClick
        this.isMouseMoveOpt = opt.isMouseMoveOpt
        this.color = this.selected >= 0 ? opt.color : getBaseColor()
        this.chartWidth = Math.min(300, Math.round(opt.width * .60))
        this.titleWidth = (opt.width - this.chartWidth) / 2
        this.minLastValue = opt.minLastValue
        this.maxLastValue = opt.maxLastValue
        this.showValue = opt.showValue ?? true

        this.yScale = getScale(getExtent([this.series], d => d.value, true), -25)
        this.xScale = getScale(opt.stepExtent, this.chartWidth)

        this.bisect = d3.bisector(function (d: PointValue) {
            return d.step
        }).left

        if (this.onClick != null && this.selected >= 1) {
            this.className = 'selected'
        } else if (this.onClick != null && this.selected == -1) {
            this.className = 'unselected'
        }

        if (this.onClick != null) {
            this.className += '.list-group-item-action'
        }
    }

    changeCursorValue(cursorStep?: number | null) {
        if (this.selected >= 0 || this.isMouseMoveOpt) {
            this.linePlot.renderIndicators(cursorStep)
            this.renderValue(cursorStep)
        }
    }

    renderValue(cursorStep?: number | null) {
        if (this.showValue === false) {
            return
        }

        const last = this.series[this.selected >= 0 || this.isMouseMoveOpt ?
            getSelectedIdx(this.series, this.bisect, cursorStep) : this.series.length - 1]

        if (Math.abs(last.value - last.smoothed) > Math.abs(last.value) / 1e6) {
            this.secondaryElem.textContent = formatFixed(last.value, 6)
        } else {
            this.secondaryElem.textContent = ''
        }
        this.primaryElem.textContent = formatFixed(last.smoothed, 6)
    }

    render($: WeyaElementFunction) {
        $(`div.sparkline-list-item.list-group-item.${this.className}`, {on: {click: this.onClick}}, $ => {
            $('div.sparkline-content', {style: {width: `${Math.min(this.titleWidth * 2 + this.chartWidth, 450)}px`}}, $ => {
                $('span', '.title', this.name, {style: {color: this.color}})
                $('svg.sparkline', {style: {width: `${this.chartWidth + this.titleWidth * 2}px`}, height: 36}, $ => {
                    $('g', {transform: `translate(${this.titleWidth}, 30)`}, $ => {
                        new LineFill({
                            series: this.series,
                            xScale: this.xScale,
                            yScale: this.yScale,
                            color: '#7f8c8d',
                            colorIdx: 9
                        }).render($)
                        this.linePlot = new LinePlot({
                            series: this.series,
                            xScale: this.xScale,
                            yScale: this.yScale,
                            color: '#7f8c8d'
                        })
                        this.linePlot.render($)
                    })
                    $('g', {transform: `translate(${this.titleWidth * 2 + this.chartWidth}, ${0})`}, $ => {
                        this.secondaryElem = $('text', '.value-secondary', {
                            style: {fill: this.color},
                            transform: `translate(${0},${12})`
                        })
                        this.primaryElem = $('text', '.value-primary', {
                            style: {fill: this.color},
                            transform: `translate(${0},${29})`
                        })
                    })
                })
            })
        })
        this.renderValue()
    }
}


export class StandaloneSparkLine {
    series: PointValue[]
    name: string
    chartWidth: number
    lastStep: number
    xScale: d3.ScaleLinear<number, number>
    yScale: d3.ScaleLinear<number, number>
    bisect: d3.Bisector<number, number>

    constructor(opt: StandaloneSparkLineOptions) {
        this.series = opt.series
        this.name = opt.name
        this.lastStep = this.series[this.series.length - 1].step
        this.chartWidth = Math.min(300, opt.width)
        this.yScale = getScale(getExtent([this.series], d => d.value, true), -25)
        this.xScale = getScale(opt.stepExtent, this.chartWidth)

        this.bisect = d3.bisector(function (d: PointValue) {
            return d.step
        }).left
    }

    render($: WeyaElementFunction) {
        $('span.standalone-sparkline', $ => {
            $('svg.sparkline', {style: {width: `${this.chartWidth}px`}, height: 50}, $ => {
                $('g',{transform: `translate(-10, 30)`}, $ => {
                    new LineFill({
                        series: this.series,
                        xScale: this.xScale,
                        yScale: this.yScale,
                        color: '#7f8c8d',
                        colorIdx: 9
                    }).render($)
                    new LinePlot({
                        series: this.series,
                        xScale: this.xScale,
                        yScale: this.yScale,
                        color: '#7f8c8d'
                    }).render($)
                })
            })
            $('span.data', $ => {
                $('span', '.name.text-muted', `${this.name}`)
                $('br')
                $('span', '.value', `${this.series[this.series.length - 1].value.toExponential(4)}`)
                $('br')
                $('span', '.step.text-secondary', `${this.lastStep}`, {style: {color: getBaseColor()}})
            })
        })
    }
}